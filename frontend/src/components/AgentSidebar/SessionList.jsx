/**
 * 会话列表组件
 * 显示历史会话，支持切换、重命名、删除
 */
import { useState } from 'react';
import { List, Typography, Spin, Input, Popconfirm, Tooltip, Empty, message } from 'antd';
import {
  MessageOutlined, DeleteOutlined, EditOutlined,
  CheckOutlined, CloseOutlined,
} from '@ant-design/icons';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;

/**
 * 格式化相对时间
 */
function formatRelativeTime(timestamp) {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;
  
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

/**
 * 单个会话项
 */
function SessionItem({
  session,
  isActive,
  onSelect,
  onRename,
  onDelete,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(session.title);
  const [isHovered, setIsHovered] = useState(false);

  const handleStartEdit = (e) => {
    e.stopPropagation();
    setEditTitle(session.title);
    setIsEditing(true);
  };

  const handleConfirmEdit = async () => {
    if (editTitle.trim() && editTitle !== session.title) {
      try {
        await onRename(session.session_id, editTitle.trim());
        message.success('重命名成功');
      } catch (error) {
        message.error('重命名失败');
      }
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditTitle(session.title);
    setIsEditing(false);
  };

  const handleDelete = async () => {
    try {
      await onDelete(session.session_id);
      message.success('会话已删除');
    } catch (error) {
      message.error('删除失败');
    }
  };

  return (
    <div
      onClick={() => !isEditing && onSelect(session.session_id)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        padding: '8px 12px',
        borderRadius: 6,
        cursor: isEditing ? 'default' : 'pointer',
        backgroundColor: isActive ? COLORS.bgHoverLight : (isHovered ? COLORS.bgHover : 'transparent'),
        borderLeft: isActive ? `3px solid ${COLORS.primary}` : '3px solid transparent',
        marginBottom: 4,
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {isEditing ? (
          <Input
            size="small"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onPressEnter={handleConfirmEdit}
            onKeyDown={(e) => e.key === 'Escape' && handleCancelEdit()}
            autoFocus
            style={{ flex: 1, marginRight: 8 }}
            suffix={
              <span>
                <CheckOutlined
                  onClick={handleConfirmEdit}
                  style={{ color: COLORS.success, cursor: 'pointer', marginRight: 4 }}
                />
                <CloseOutlined
                  onClick={handleCancelEdit}
                  style={{ color: COLORS.textSecondary, cursor: 'pointer' }}
                />
              </span>
            }
          />
        ) : (
          <>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ 
                fontSize: 13, 
                fontWeight: isActive ? 500 : 400,
                color: isActive ? COLORS.textPrimary : COLORS.textSecondary,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {session.title}
              </div>
              <div style={{ 
                fontSize: 11, 
                color: COLORS.textTertiary,
                marginTop: 2,
              }}>
                <MessageOutlined style={{ marginRight: 4 }} />
                {session.turn_count} 轮 · {formatRelativeTime(session.updated_at)}
              </div>
            </div>
            
            {isHovered && !isActive && (
              <div style={{ display: 'flex', gap: 4 }} onClick={(e) => e.stopPropagation()}>
                <Tooltip title="重命名">
                  <EditOutlined
                    onClick={handleStartEdit}
                    style={{ 
                      color: COLORS.textSecondary, 
                      cursor: 'pointer',
                      fontSize: 12,
                    }}
                  />
                </Tooltip>
                <Popconfirm
                  title="确定删除此会话？"
                  onConfirm={handleDelete}
                  okText="删除"
                  cancelText="取消"
                  placement="left"
                >
                  <DeleteOutlined
                    style={{ 
                      color: COLORS.textSecondary, 
                      cursor: 'pointer',
                      fontSize: 12,
                    }}
                  />
                </Popconfirm>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * 会话列表组件
 */
export function SessionList({
  sessions,
  currentSessionId,
  loading,
  error,
  onSelect,
  onRename,
  onDelete,
  maxHeight = 200,
}) {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <Spin size="small" />
        <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
          加载会话列表...
        </Text>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '12px 0' }}>
        <Text type="danger" style={{ fontSize: 12 }}>
          加载失败：{error}
        </Text>
      </div>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={<Text type="secondary" style={{ fontSize: 12 }}>暂无历史会话</Text>}
        style={{ margin: '12px 0' }}
      />
    );
  }

  return (
    <div style={{ 
      maxHeight, 
      overflowY: 'auto',
      overflowX: 'hidden',
    }}>
      {sessions.map((session) => (
        <SessionItem
          key={session.session_id}
          session={session}
          isActive={session.session_id === currentSessionId}
          onSelect={onSelect}
          onRename={onRename}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}

export default SessionList;
