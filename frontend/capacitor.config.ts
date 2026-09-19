import type { CapacitorConfig } from '@capacitor/cli';

/**
 * 学海智导 Capacitor 配置
 * 将 Vite 构建产物（dist/）包装为原生 Android/iOS 应用壳。
 * 使用步骤见 frontend/README.md「打包为手机 App」一节。
 */
const config: CapacitorConfig = {
  appId: 'com.xuehai.zhidao',
  appName: '学海智导',
  webDir: 'dist',
  backgroundColor: '#FBF1E7',
  android: {
    backgroundColor: '#FBF1E7',
  },
  ios: {
    backgroundColor: '#FBF1E7',
  },
};

export default config;
