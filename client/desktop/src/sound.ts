/** 提示音：WebAudio 播放打包内置 ding.wav */
import dingUrl from "./assets/ding.wav";

let ctx: AudioContext | null = null;
let buffer: AudioBuffer | null = null;

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
  } catch {
    /* 无声环境忽略 */
  }
}
