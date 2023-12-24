// 引入Vue.js和Vue Router
import Vue from 'vue';
import VueRouter from 'vue-router';

// 引入Vue组件
import Page1Component from './Page1Component.vue';
import Page2Component from './Page2Component.vue';

// 使用Vue Router插件
Vue.use(VueRouter);

// 配置路由
const routes = [
  { path: '/page1', component: Page1Component },
  { path: '/page2', component: Page2Component },
  // 其他页面的路由配置
];

const router = new VueRouter({
  routes
});

// 创建Vue实例
new Vue({
  el: '#app',
  router
});
