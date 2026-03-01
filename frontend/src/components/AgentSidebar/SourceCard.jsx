import { memo } from 'react';
import { Card, Typography, Tag, Collapse } from 'antd';
import { FileTextOutlined, LinkOutlined } from '@ant-design/icons';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;

const SourceCard = memo(function SourceCard({ source, index, onOpenChunk }) {
  return (
    <Card
      key={index}
      size="small"
      title={
        <span style={{ color: COLORS.rag, fontSize: 13 }}>
          <LinkOutlined style={{ marginRight: 4 }} />
          {source.filename}
        </span>
      }
      extra={source.score && <Tag color="purple">{(source.score * 100).toFixed(0)}%</Tag>}
      style={{
        marginBottom: 8,
        cursor: 'pointer',
        borderLeft: `3px solid ${COLORS.rag}`,
        borderRadius: 6,
      }}
      hoverable
      onClick={() => onOpenChunk(source, index)}
    >
      <Text ellipsis={{ rows: 2 }} style={{ fontSize: 12, color: COLORS.textSecondary }}>
        {source.content}
      </Text>
    </Card>
  );
});

const SourceList = memo(function SourceList({ sources, onOpenChunk }) {
  if (!sources || sources.length === 0) return null;

  return (
    <Collapse
      ghost
      style={{ marginTop: 12 }}
      items={[{
        key: 'sources',
        label: (
          <span style={{ color: COLORS.rag, fontWeight: 500 }}>
            <FileTextOutlined /> 引用来源 ({sources.length})
          </span>
        ),
        children: sources.map((source, i) => (
          <SourceCard key={i} source={source} index={i} onOpenChunk={onOpenChunk} />
        ))
      }]}
    />
  );
});

export { SourceCard, SourceList };
export default SourceList;
