// Generated markup: chapter cards and camera pans.
(function () {
  window.beforeInit = function (T) {
    // cost: CBAM factor 2026-2034, the free-allowance deduction as % of the EU benchmark (Regulation (EU) 2023/956 Art. 31)
    const box = document.getElementById('pbars');
    if (box && !box.children.length) [97.5, 95, 90, 77.5, 51.5, 39, 26.5, 14, 0].forEach((v, i) => {
      const d = document.createElement('div');
      d.className = 'pb';
      d.innerHTML = `<em class="a fade" data-c="5" data-o="${(1.4 + i * 0.45).toFixed(2)}">${v}%</em><i class="a growy" data-c="5" data-o="${(1.2 + i * 0.45).toFixed(2)}" style="height:${Math.max(6, v * 3.6)}px"></i><span>${2026 + i}</span>`;
      box.appendChild(d);
    });
    T.scenes.forEach(info => {
      const sec = document.getElementById(info.id);
      // chapter card: shown during the lead-in, leaves just after the first line starts
      if (sec.dataset.num) {
        const card = document.createElement('div');
        card.className = 'chapcard a fade';
        const L0 = info.lines[0].start;
        card.dataset.cd = '0.05';
        card.dataset.o = (-L0).toFixed(3);
        card.dataset.x = '0'; card.dataset.xo = '0.9';
        card.innerHTML = `<div class="cn a up" data-o="${(0.1 - L0).toFixed(3)}">${sec.dataset.num}</div>
          <div class="cline a growx" data-o="${(0.25 - L0).toFixed(3)}"></div>
          <div class="ct a up" data-o="${(0.35 - L0).toFixed(3)}">${info.chapter}</div>`;
        sec.appendChild(card);
        info.cardEnd = info.lines[0].start + 0.9;
      }
      // horizontal camera pan: data-pan="line:x,line:x,..." on a track element
      sec.querySelectorAll('[data-pan]').forEach(track => {
        const steps = track.dataset.pan.split(',').map(p => p.split(':').map(Number));
        const total = info.dur;
        const at = ([line, off]) => Math.min(0.995, (info.lines[line].start + (off || 0)) / total);
        const frames = [{ offset: 0, transform: 'translateX(0px)' }];
        let prev = 'translateX(0px)';
        steps.forEach(([line, x, off]) => {
          const o = at([line, (off || 0) + 0.9]);
          const hold = Math.max(frames[frames.length - 1].offset, o - 1.4 / total);
          frames.push({ offset: hold, transform: prev });
          prev = `translateX(${x}px)`;
          frames.push({ offset: o, transform: prev, easing: 'linear' });
        });
        // ease each move: keyframe pairs (hold -> target) use a smooth curve
        for (let i = 1; i < frames.length; i += 2) frames[i].easing = 'cubic-bezier(.65,0,.35,1)';
        frames.push({ offset: 1, transform: prev });
        track.animate(frames, { duration: total * 1000, delay: info.start * 1000, fill: 'both' }).pause();
      });
    });
  };
})();
