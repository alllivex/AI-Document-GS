import { createRouter, createWebHistory } from 'vue-router'

import TaskCreateView from './views/TaskCreateView.vue'
import DocumentTraceView from './views/DocumentTraceView.vue'
import TaskListView from './views/TaskListView.vue'
import TaskResultView from './views/TaskResultView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/tasks',
    },
    {
      path: '/tasks',
      component: TaskListView,
    },
    {
      path: '/tasks/create',
      component: TaskCreateView,
    },
    {
      path: '/tasks/:taskId/results',
      component: TaskResultView,
    },
    {
      path: '/documents/:docId',
      component: DocumentTraceView,
    },
  ],
})

export default router
