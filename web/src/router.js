import { createRouter, createWebHashHistory } from 'vue-router'
import { getToken } from './auth'

const routes = [
  { path: '/login', component: () => import('./views/Login.vue') },
  {
    path: '/',
    component: () => import('./views/Layout.vue'),
    redirect: '/overview',
    children: [
      { path: 'overview', component: () => import('./views/Overview.vue'), meta: { title: '总览' } },
      { path: 'terminals', component: () => import('./views/Terminals.vue'), meta: { title: '终端管理' } },
      { path: 'messages', component: () => import('./views/Messages.vue'), meta: { title: '消息记录' } },
      { path: 'apikeys', component: () => import('./views/ApiKeys.vue'), meta: { title: 'API 密钥' } },
      { path: 'push', component: () => import('./views/Push.vue'), meta: { title: '发送消息' } },
    ],
  },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  if (to.path !== '/login' && !getToken()) return '/login'
})

export default router
