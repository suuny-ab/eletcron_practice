import axios from 'axios';

// 后端 API 基础 URL（开发环境）
const API_BASE_URL = 'http://localhost:8000';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 获取知识库文件树
 */
export const getFileTree = async () => {
  const response = await apiClient.get('/knowledge/tree');
  return response.data;
};

/**
 * 读取文件内容
 * @param {string} relativePath - 相对路径
 */
export const getFileContent = async (relativePath) => {
  const response = await apiClient.get(`/knowledge/file/${relativePath}`);
  return response.data;
};
