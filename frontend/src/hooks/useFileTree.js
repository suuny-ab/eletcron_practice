/**
 * 文件树状态管理 Hook
 * 负责文件树数据的加载、展开/收起状态管理
 */
import { useState, useRef, useCallback } from 'react';
import { message } from 'antd';
import { getFileTree } from '../api/knowledge';

export function useFileTree() {
  const [treeData, setTreeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState([]);
  const [selectedKeys, setSelectedKeys] = useState([]);
  const hasInitialized = useRef(false);

  // 获取所有可展开的节点 key
  const getAllExpandableKeys = useCallback((nodes) => {
    let keys = [];
    nodes.forEach(node => {
      if (node.children) {
        keys.push(node.key);
        keys = keys.concat(getAllExpandableKeys(node.children));
      }
    });
    return keys;
  }, []);

  // 加载文件树
  const loadTree = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getFileTree();
      setTreeData(response.data.tree);
      message.success('文件树加载成功');
      return response.data.tree;
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('请先配置知识库路径');
      } else {
        message.error('加载文件树失败: ' + (error.response?.data?.message || error.message));
      }
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始化加载
  const initializeTree = useCallback(async () => {
    if (!hasInitialized.current) {
      hasInitialized.current = true;
      return await loadTree();
    }
    return treeData;
  }, [loadTree, treeData]);

  // 切换展开/收起所有节点
  const toggleExpandAll = useCallback(() => {
    if (expandedKeys.length === 0) {
      setExpandedKeys(getAllExpandableKeys(treeData));
    } else {
      setExpandedKeys([]);
    }
  }, [expandedKeys, treeData, getAllExpandableKeys]);

  // 刷新文件树
  const refreshTree = useCallback(async () => {
    return await loadTree();
  }, [loadTree]);

  return {
    // 状态
    treeData,
    loading,
    expandedKeys,
    selectedKeys,
    
    // 状态设置器
    setExpandedKeys,
    setSelectedKeys,
    
    // 方法
    initializeTree,
    refreshTree,
    toggleExpandAll,
    getAllExpandableKeys,
  };
}

export default useFileTree;
