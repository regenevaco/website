"""Stage 4: photoreal ReGeneva studio background, rendered in Blender Cycles.

    python3 studio.py <logo_png> <out.png> [width] [height] [samples]

A dark charcoal studio wall seen through a 35 mm lens focused on the presenter (1.2 m) at f/2.2,
so the set falls naturally out of focus, as it would on a real camera:
  - walnut slat acoustic panel (right) with a ReGeneva-green LED reveal
  - floating walnut shelves (left) with books, a ceramic vase and a plant
  - halo-lit acrylic ReGeneva sign (upper left)
  - warm practical lamp (far right) and a soft background light pooling on the wall behind the presenter
"""
import math
import os
import sys

import bpy
import numpy as np
from PIL import Image, ImageFilter

GREEN = (0x20 / 255, 0xC9 / 255, 0x97 / 255)


def srgb_to_lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mat(name, color, rough=0.6, emit=None, strength=0.0, metallic=0.0, tex=None, noise=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if noise:   # subtle plaster / wood variation
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = noise[0]
        n.inputs["Detail"].default_value = 8
        ramp = nt.nodes.new("ShaderNodeMixRGB")
        ramp.blend_type = "MULTIPLY"
        ramp.inputs["Fac"].default_value = noise[1]
        ramp.inputs["Color1"].default_value = (*color, 1)
        nt.links.new(n.outputs["Fac"], ramp.inputs["Color2"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.08
        nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if tex:     # image-driven emission + alpha (logo / halo)
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(tex)
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    return m


def box(name, loc, size, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    o.data.materials.append(material)
    bpy.ops.object.transform_apply(scale=True)
    bev = o.modifiers.new("bev", "BEVEL")
    bev.width = min(size) * 0.08
    bev.segments = 2
    return o


def plane(name, loc, w, h, material, rot=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (w / 2, h / 2, 1)
    o.data.materials.append(material)
    return o


def main(logo, out, width=3840, height=2160, samples=128):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(samples)
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = int(width), int(height)
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "16"
    sc.render.threads_mode = "FIXED"
    sc.render.threads = 4

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.004, 0.005, 1)
    sc.world = world

    # Camera: 35 mm full frame, eye level, focused on the presenter at 1.2 m.
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 35
    cam_d.sensor_width = 36
    cam_d.dof.use_dof = True
    cam_d.dof.focus_distance = 1.2
    cam_d.dof.aperture_fstop = 2.2
    cam_d.dof.aperture_blades = 9
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (0, 0, 1.22)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam

    WALL_Y = 2.9
    charcoal = mat("charcoal", srgb_to_lin((0.115, 0.12, 0.125)), rough=0.85, noise=(18, 0.25))
    walnut = mat("walnut", srgb_to_lin((0.33, 0.2, 0.12)), rough=0.45, noise=(60, 0.45))
    felt = mat("felt", srgb_to_lin((0.03, 0.03, 0.032)), rough=1.0)
    floor_m = mat("floor", srgb_to_lin((0.16, 0.13, 0.11)), rough=0.35, noise=(4, 0.3))

    plane("wall", (0, WALL_Y, 1.5), 9, 4, charcoal)
    plane("floor", (0, 1.5, 0), 9, 4, floor_m, rot=(0, 0, 0))
    plane("ceiling", (0, 1.5, 3.0), 9, 4, charcoal, rot=(math.pi, 0, 0))

    # Walnut slat panel, right side, on black felt, with a green LED reveal on its left edge.
    x0, x1 = 0.62, 2.6
    plane("felt", (0.5 * (x0 + x1), WALL_Y - 0.005, 1.25), x1 - x0, 2.5, felt)
    x = x0 + 0.02
    while x < x1:
        box("slat", (x, WALL_Y - 0.02, 1.25), (0.034, 0.024, 2.5), walnut)
        x += 0.052
    led = mat("led", (0, 0, 0), emit=srgb_to_lin(GREEN), strength=5)
    plane("led_strip", (x0 - 0.035, WALL_Y - 0.03, 1.25), 0.012, 2.5, led, rot=(math.pi / 2, 0, math.radians(90)))
    gl = bpy.data.lights.new("led_glow", "AREA")
    gl.shape = "RECTANGLE"
    gl.size, gl.size_y = 0.02, 2.5
    gl.energy = 14
    gl.color = srgb_to_lin(GREEN)
    o = bpy.data.objects.new("led_glow", gl)
    sc.collection.objects.link(o)
    o.location = (x0 - 0.03, WALL_Y - 0.06, 1.25)
    o.rotation_euler = (math.radians(90), 0, math.radians(90))

    # Floating shelves, left side, with objects.
    for z in (0.98, 1.38):
        box("shelf", (-0.98, WALL_Y - 0.13, z), (0.95, 0.24, 0.035), walnut)
    book_cols = [(0.62, 0.6, 0.55), (0.09, 0.27, 0.22), (0.2, 0.2, 0.22), (0.55, 0.35, 0.22)]
    bx = -1.36
    for i, c in enumerate(book_cols):
        h = 0.2 + 0.03 * ((i * 7) % 3)
        box("book", (bx, WALL_Y - 0.14, 1.0 + h / 2), (0.035, 0.17, h), mat(f"b{i}", srgb_to_lin(c), 0.7))
        bx += 0.04
    box("book_flat", (-1.18, WALL_Y - 0.14, 1.415), (0.22, 0.16, 0.035), mat("bf", srgb_to_lin((0.85, 0.83, 0.78)), 0.7))
    box("book_flat2", (-1.18, WALL_Y - 0.14, 1.45), (0.19, 0.15, 0.03), mat("bf2", srgb_to_lin((0.12, 0.33, 0.27)), 0.7))
    ceramic = mat("ceramic", srgb_to_lin((0.86, 0.84, 0.8)), 0.35)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=0.17, location=(-0.72, WALL_Y - 0.13, 1.083))
    v = bpy.context.object
    v.data.materials.append(ceramic)
    bev = v.modifiers.new("bev", "BEVEL")
    bev.width, bev.segments = 0.01, 3
    bpy.ops.object.shade_smooth()
    # Snake plant: tall blades fanning out of the vase, leaning in the wall plane.
    leaf_m = mat("leaf", srgb_to_lin((0.2, 0.4, 0.2)), 0.5)
    rng = np.random.default_rng(3)
    for k in range(9):
        lean = rng.uniform(-0.45, 0.45)
        ln = rng.uniform(0.2, 0.3)
        cx = -0.72 + math.sin(lean) * ln / 2
        cz = 1.16 + math.cos(lean) * ln / 2
        box("leaf", (cx, WALL_Y - 0.13 + rng.uniform(-0.03, 0.03), cz), (0.035, 0.006, ln), leaf_m,
            rot=(rng.uniform(-0.2, 0.2), lean, rng.uniform(-0.6, 0.6)))
    brass = mat("brass", srgb_to_lin((0.78, 0.6, 0.3)), 0.3, metallic=1.0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(-0.62, WALL_Y - 0.13, 1.442))
    bpy.context.object.data.materials.append(brass)
    bpy.ops.object.shade_smooth()

    # Halo-lit acrylic ReGeneva sign, upper left: white letters + soft halo on the wall behind.
    logo_w = 0.78
    im = Image.open(logo).convert("RGBA")
    lw, lh = im.size
    pad = 120
    canvas = Image.new("RGBA", (lw + 2 * pad, lh + 2 * pad), (0, 0, 0, 0))
    canvas.paste(im, (pad, pad))
    halo = canvas.copy()
    a = halo.split()[3].filter(ImageFilter.GaussianBlur(28))
    halo = Image.merge("RGBA", (*Image.new("RGB", halo.size, (255, 255, 255)).split(), a.point(lambda v: int(v * 0.85))))
    d = os.path.dirname(os.path.abspath(out))
    letters_p, halo_p = os.path.join(d, "_logo_letters.png"), os.path.join(d, "_logo_halo.png")
    canvas.save(letters_p)
    halo.save(halo_p)
    sw = logo_w * (lw + 2 * pad) / lw
    sh = sw * (lh + 2 * pad) / (lw + 2 * pad)
    cx, cz = -0.86, 1.78
    letters = mat("letters", (1, 1, 1), 0.3, emit=(1, 1, 1), strength=2.2, tex=letters_p)
    plane("logo", (cx, WALL_Y - 0.035, cz), sw, sh, letters)
    halo_m = mat("halo", (0, 0, 0), 1.0, emit=(1, 1, 1), strength=0.9, tex=halo_p)
    plane("logo_halo", (cx, WALL_Y - 0.004, cz), sw * 1.04, sh * 1.04, halo_m)

    # Warm practical lamp, far right (becomes a soft bokeh highlight).
    shade = mat("shade", (0, 0, 0), 0.9, emit=srgb_to_lin((1.0, 0.78, 0.5)), strength=2.5)
    bpy.ops.mesh.primitive_cone_add(radius1=0.16, radius2=0.11, depth=0.22, location=(1.22, 2.7, 1.62))
    bpy.context.object.data.materials.append(shade)
    lamp = bpy.data.lights.new("lamp", "POINT")
    lamp.energy = 25
    lamp.color = (1.0, 0.72, 0.45)
    lamp.shadow_soft_size = 0.15
    o = bpy.data.objects.new("lamp", lamp)
    sc.collection.objects.link(o)
    o.location = (1.22, 2.7, 1.59)
    box("lamp_pole", (1.22, 2.7, 0.75), (0.025, 0.025, 1.46), mat("pole", srgb_to_lin((0.05, 0.05, 0.05)), 0.4, metallic=1))

    # Background light: soft warm-neutral pool on the wall behind the presenter.
    bg = bpy.data.lights.new("bg", "SPOT")
    bg.energy = 420
    bg.spot_size = math.radians(70)
    bg.spot_blend = 1.0
    bg.shadow_soft_size = 0.6
    bg.color = (1.0, 0.93, 0.85)
    o = bpy.data.objects.new("bg", bg)
    sc.collection.objects.link(o)
    o.location = (0.0, 1.3, 2.9)
    o.rotation_euler = (math.radians(35), 0, 0)
    # Gentle fill so the set reads, not black.
    fill = bpy.data.lights.new("fill", "AREA")
    fill.size = 3
    fill.energy = 90
    fill.color = (0.9, 0.95, 1.0)
    o = bpy.data.objects.new("fill", fill)
    sc.collection.objects.link(o)
    o.location = (0, -0.5, 2.4)
    o.rotation_euler = (math.radians(70), 0, 0)

    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("wrote", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], *(a[2:5]))
