import { memo, useRef, useEffect } from 'react';
import { Button, Typography, Tag, Space } from 'antd';
import { CheckOutlined, CloseOutlined, SwapOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { remarkPlugins, rehypePlugins, createMarkdownComponents } from '../../utils/markdownStyles.jsx';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;

/**
 * 双栏对比标签页 - 在主区域展示文档修改前后 Markdown 渲染对比
 * 左侧渲染原始文档，右侧渲染修改后文档
 * 双栏同步滚动
 */
const DiffTab = memo(function DiffTab({
  originalContent,
  editedContent,
  documentName,
  onConfirm,
  onCancel,
}) {
  const leftRef = useRef(null);
  const rightRef = useRef(null);

  // 同步滚动：拦截 wheel 事件，手动对两个面板施加相同 deltaY
  useEffect(() => {
    const left = leftRef.current;
    const right = rightRef.current;
    if (!left || !right) return;

    const handler = (e) => {
      e.preventDefault();
      const delta = e.deltaY;
      left.scrollTop += delta;
      right.scrollTop += delta;
    };

    left.addEventListener('wheel', handler, { passive: false });
    right.addEventListener('wheel', handler, { passive: false });
    return () => {
      left.removeEventListener('wheel', handler);
      right.removeEventListener('wheel', handler);
    };
  }, []);

  const original = originalContent || '';
  const edited = editedContent || '';
  const origLen = original.length;
  const editLen = edited.length;
  const diff = editLen - origLen;

  const panelStyle = {
    flex: 1,
    overflow: 'auto',
    padding: '24px',
    backgroundColor: COLORS.bgCard,
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#fff' }}>
      {/* 标题栏 */}
      <div style={{
        padding: '10px 20px',
        borderBottom: `1px solid ${COLORS.borderLight}`,
        background: '#fafafa',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <Space size={12}>
          <Text strong style={{ fontSize: 15 }}>
            <SwapOutlined style={{ marginRight: 6 }} />
            变更对比
          </Text>
          {documentName && (
            <Tag style={{ fontSize: 12 }}>{documentName}</Tag>
          )}
          <Tag color={diff >= 0 ? 'green' : 'red'} style={{ fontSize: 11 }}>
            {diff >= 0 ? '+' : ''}{diff} 字符
          </Tag>
        </Space>
        <Space>
          <Button icon={<CloseOutlined />} onClick={onCancel}>
            取消
          </Button>
          <Button type="primary" icon={<CheckOutlined />} onClick={() => onConfirm(editedContent)}>
            确认保存
          </Button>
        </Space>
      </div>

      {/* 双栏区域标题 */}
      <div style={{
        display: 'flex',
        borderBottom: `1px solid ${COLORS.borderLight}`,
        flexShrink: 0,
      }}>
        <div style={{
          flex: 1,
          padding: '6px 20px',
          background: '#fafafa',
          fontSize: 12,
          fontWeight: 600,
          color: COLORS.textSecondary,
          borderRight: `2px solid ${COLORS.border}`,
        }}>
          原始文档 ({origLen} 字符)
        </div>
        <div style={{
          flex: 1,
          padding: '6px 20px',
          background: '#f0faf0',
          fontSize: 12,
          fontWeight: 600,
          color: '#22863a',
        }}>
          修改后 ({editLen} 字符)
        </div>
      </div>

      {/* 双栏内容 */}
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
        minHeight: 0,
      }}>
        {/* 左侧 - 原始文档 Markdown 渲染 */}
        <div
          ref={leftRef}
          style={{
            ...panelStyle,
            borderRight: `2px solid ${COLORS.border}`,
          }}
        >
          {original ? (
            <ReactMarkdown
              remarkPlugins={remarkPlugins}
              rehypePlugins={rehypePlugins}
              components={createMarkdownComponents('full')}
            >
              {original}
            </ReactMarkdown>
          ) : (
            <Text type="secondary">（空文档）</Text>
          )}
        </div>

        {/* 右侧 - 修改后文档 Markdown 渲染 */}
        <div
          ref={rightRef}
          style={panelStyle}
        >
          {edited ? (
            <ReactMarkdown
              remarkPlugins={remarkPlugins}
              rehypePlugins={rehypePlugins}
              components={createMarkdownComponents('full')}
            >
              {edited}
            </ReactMarkdown>
          ) : (
            <Text type="secondary">（空文档）</Text>
          )}
        </div>
      </div>
    </div>
  );
});

export default DiffTab;
