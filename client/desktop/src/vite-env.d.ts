/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

/** 内置提示音资源 */
declare module "*.wav" {
  const src: string;
  export default src;
}
