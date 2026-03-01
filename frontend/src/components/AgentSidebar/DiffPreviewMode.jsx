import { memo, useMemo } from 'react';
import { Button, Typography, Tag, Space } from 'antd';
import { CheckOutlined, CloseOutlined, FileTextOutlined, SwapOutlined } from '@ant-design/icons';
import { applyPatch, diffLines } from 'diff';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;

/**
 * Diff 预览模式
 * 接收原始文档和 diff 字符串，展示行级差异对比
 */
const DiffPreviewMode = memo(function DiffPreviewMode({
  originalContent,
  diffContent,
  onConfirm,
  onCancel,
}) {
  // 计算 patched 结果和行级差异
  const { patchedContent, changes, stats, patchError } = useMemo(() => {
    if (!diffContent) {
      return { patchedContent: null, changes: [], stats: { added: 0, removed: 0 }, patchError: true };
    }

    try {
      // 尝试应用 patch
      const patched = applyPatch(originalContent || '', diffContent);

      if (patched === false) {
        // patch 应用失败，解析 diff 本身展示
        return {
          patchedContent: null,
          changes: parseDiffLines(diffContent),
          stats: countDiffStats(diffContent),
          patchError: true,
        };
      }

      // patch 成功，用 diffLines 计算行级差异用于渲染
      const lineChanges = diffLines(originalContent || '', patched);
      let added = 0;
      let removed = 0;
      const formattedChanges = [];

      for (const change of lineChanges) {
        const lines = change.value.replace(/\n$/, '').split('\n');
        for (const line of lines) {
          if (change.added) {
            formattedChanges.push({ type: 'add', content: line });
            added++;
          } else if (change.removed) {
            formattedChanges.push({ type: 'remove', content: line });
            removed++;
          } else {
            formattedChanges.push({ type: 'equal', content: line });
          }
        }
      }

      return {
        patchedContent: patched,
        changes: formattedChanges,
        stats: { added, removed },
        patchError: false,
      };
    } catch {
      // applyPatch 或 diffLines 抛异常时降级处理
      return {
        patchedContent: null,
        changes: parseDiffLines(diffContent),
        stats: countDiffStats(diffContent),
        patchError: true,
      };
    }
  }, [originalContent, diffContent]);

  // 行样式
  const getLineStyle = (type) => {
    const base = {
      padding: '1px 8px',
      fontFamily: 'Consolas, Monaco, "Courier New", monospace',
      fontSize: 12,
      lineHeight: '20px',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-all',
    };
    switch (type) {
      case 'add':
        return { ...base, background: '#e6ffed', color: '#22863a', borderLeft: '3px solid #22863a' };
      case 'remove':
        return { ...base, background: '#ffeef0', color: '#cb2431', borderLeft: '3px solid #cb2431', textDecoration: 'line-through' };
      default:
        return { ...base, background: 'transparent', color: COLORS.textSecondary, borderLeft: '3px solid transparent' };
    }
  };

  const getLinePrefix = (type) => {
    switch (type) {
      case 'add': return '+';
      case 'remove': return '-';
      default: return ' ';
    }
  };

  return (
    <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      {/* 标题栏 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: `1px solid ${COLORS.borderLight}`,
        background: '#fafafa',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space size={8}>
            <Text strong style={{ fontSize: 14 }}>
              <SwapOutlined style={{ marginRight: 4 }} /> 变更预览
            </Text>
            {patchError && (
              <Tag color="warning" style={{ fontSize: 11 }}>Diff 格式预览</Tag>
            )}
          </Space>
          <Space size={4}>
            <Tag color="green" style={{ fontSize: 11 }}>+{stats.added}</Tag>
            <Tag color="red" style={{ fontSize: 11 }}>-{stats.removed}</Tag>
          </Space>
        </div>
      </div>

      {/* Diff 内容区 */}
      <div style={{
        flex: 1,
        minHeight: 0,
        overflow: 'auto',
        padding: '8px 0',
      }}>
        {patchError && !changes.length ? (
          <div style={{ padding: 16, color: COLORS.textSecondary, fontSize: 13 }}>
            <Text type="warning">无法解析 Diff 内容，请检查格式。</Text>
            <pre style={{
              marginTop: 8,
              padding: 12,
              background: '#1e1e1e',
              color: '#d4d4d4',
              borderRadius: 6,
              fontSize: 12,
              lineHeight: 1.5,
              overflow: 'auto',
            }}>
              {diffContent}
            </pre>
          </div>
        ) : (
          <div>
            {changes.map((change, index) => (
              <div key={index} style={getLineStyle(change.type)}>
                <span style={{
                  display: 'inline-block',
                  width: 16,
                  color: change.type === 'add' ? '#22863a' : change.type === 'remove' ? '#cb2431' : '#999',
                  fontWeight: 600,
                  userSelect: 'none',
                }}>
                  {getLinePrefix(change.type)}
                </span>
                {change.content}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 操作栏 */}
      <div style={{
        padding: '12px',
        borderTop: `1px solid ${COLORS.borderLight}`,
        display: 'flex',
        gap: '8px',
      }}>
        <Button
          icon={<CloseOutlined />}
          onClick={onCancel}
          style={{ flex: 1 }}
        >
          取消
        </Button>
        <Button
          type="primary"
          icon={<CheckOutlined />}
          onClick={() => onConfirm(patchedContent)}
          disabled={patchError || !patchedContent}
          style={{ flex: 1 }}
        >
          确认保存
        </Button>
      </div>
    </div>
  );
});

/**
 * 从 raw diff 字符串解析行 (fallback，当 applyPatch 失败时)
 */
function parseDiffLines(diffStr) {
  const lines = diffStr.split('\n');
  const changes = [];
  for (const line of lines) {
    if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
      // diff 头信息，作为上下文展示
      changes.push({ type: 'equal', content: line });
    } else if (line.startsWith('+')) {
      changes.push({ type: 'add', content: line.slice(1) });
    } else if (line.startsWith('-')) {
      changes.push({ type: 'remove', content: line.slice(1) });
    } else if (line.startsWith(' ')) {
      changes.push({ type: 'equal', content: line.slice(1) });
    } else {
      changes.push({ type: 'equal', content: line });
    }
  }
  return changes;
}

/**
 * 从 raw diff 字符串统计增删行数
 */
function countDiffStats(diffStr) {
  const lines = diffStr.split('\n');
  let added = 0;
  let removed = 0;
  for (const line of lines) {
    if (line.startsWith('+') && !line.startsWith('+++')) added++;
    if (line.startsWith('-') && !line.startsWith('---')) removed++;
  }
  return { added, removed };
}

export default DiffPreviewMode;
