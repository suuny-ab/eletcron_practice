import axios from 'axios';

// 后端 API 基础 URL（开发环境）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 读取配置
 */
export const getConfig = async () => {
  const response = await apiClient.get('/config');
  return response.data;
};

/**
 * 更新配置
 */
export const updateConfig = async (configData) => {
  const response = await apiClient.put('/config', configData);
  return response.data;
};

/**
 * 删除配置
 */
export const deleteConfig = async () => {
  const response = await apiClient.delete('/config');
  return response.data;
};
