import { memo } from 'react';
import { Tree, Spin, Button, Empty } from 'antd';
import { FolderOutlined, FileOutlined, ReloadOutlined, FolderOpenOutlined } from '@ant-design/icons';
import { COLORS } from '../../styles/tokens';

const { DirectoryTree } = Tree;

const FileTree = memo(function FileTree({ treeData, loading, expandedKeys, selectedKeys, onExpand, onSelect, onRefresh, onToggleExpandAll }) {
  return (
    <div style={{ height: '100%', background: COLORS.bgCard, display: 'flex', flexDirection: 'column' }}>
      <div style={{
        padding: '16px',
        borderBottom: `1px solid ${COLORS.borderLight}`,
        background: COLORS.bgCard,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <Button
          type="text"
          size="small"
          icon={expandedKeys.length > 0 ? <FolderOutlined /> : <FolderOpenOutlined />}
          onClick={onToggleExpandAll}
          style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        />
        <Button
          type="text"
          size="small"
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        />
      </div>

      <div style={{ padding: '16px', flex: 1, overflowY: 'auto' }}>
        <Spin spinning={loading}>
          {treeData.length > 0 ? (
            <DirectoryTree
              showIcon
              expandedKeys={expandedKeys}
              onExpand={onExpand}
              selectedKeys={selectedKeys}
              onSelect={onSelect}
              treeData={treeData}
              icon={({ is_leaf }) =>
                is_leaf ? <FileOutlined style={{ color: COLORS.info }} /> : <FolderOutlined style={{ color: COLORS.warning }} />
              }
              style={{ fontSize: 14 }}
            />
          ) : (
            <Empty
              description="暂无文件"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ marginTop: 60 }}
            />
          )}
        </Spin>
      </div>
    </div>
  );
});

export default FileTree;
