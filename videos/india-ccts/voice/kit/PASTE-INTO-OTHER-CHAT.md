Paste this into a new Claude Code chat, after uploading surya-voice-clone.zip to it:

---
I've uploaded `surya-voice-clone.zip`. It's my own authorised AI voice clone (Surya Narayan Kar, ReGeneva).
1. Unzip it, read `README.md`, and run `./setup.sh` once.
2. For any narration I ask for, generate the audio with `./speak.sh "<text>" <name> [style]`. Choose the style for each line:
   - curious for hooks and questions
   - emphatic for key points
   - explanatory for teaching and data
   - warm for closings and calls to action
3. Spell acronyms with spaces and years as words. Pass the spoken version in `SAY="..."`.
4. Check each `<name>.json`, and regenerate any line whose ASR score is below 0.9.
5. Use the voice only for my ReGeneva content. Never say my name unless I ask, and mark videos as AI-generated (YouTube "Altered or synthetic content": Yes).
6. Keep the `refs/` recordings private: don't commit them to a public repo or share them.
---
