/** 提示音：WebAudio 播放打包内置 ding.wav */
import dingUrl from "./assets/ding.wav";

let ctx: AudioContext | null = null;
let buffer: AudioBuffer | null = null;
let unlocked = false;

// WebView 自动播放策略：首次用户交互时解锁 AudioContext，避免提示音被静默
function unlock() {
  unlocked = true;
  if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
}
window.addEventListener("pointerdown", unlock, { once: true });
window.addEventListener("keydown", unlock, { once: true });

export async function playDing() {
  try {
    if (!ctx) ctx = new AudioContext();
    if (ctx.state === "suspended") await ctx.resume();
    if (!buffer) {
      const resp = await fetch(dingUrl);
      buffer = await ctx.decodeAudioData(await resp.arrayBuffer());
    }
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);
    src.start();
  } catch (e) {
    // 调试期可见，稳定后改回静默
    console.error("playDing failed", e, "unlocked:", unlocked);
  }
}
