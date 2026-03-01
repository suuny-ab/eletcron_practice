import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * 获取健康详情
 */
export const fetchHealthDetail = async () => {
  const response = await apiClient.get('/api/health/detail');
  return response.data;
};

/**
 * 获取实时指标快照
 */
export const fetchMetrics = async () => {
  const response = await apiClient.get('/api/health/metrics');
  return response.data;
};

/**
 * 获取时序数据
 * @param {number} minutes - 返回最近 N 分钟的数据 (1-60)
 */
export const fetchTimeseries = async (minutes = 60) => {
  const response = await apiClient.get('/api/health/timeseries', {
    params: { minutes },
  });
  return response.data;
};
