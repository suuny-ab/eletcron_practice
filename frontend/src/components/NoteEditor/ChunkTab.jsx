import { Card, Typography, Empty, Space, Tag } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { remarkPlugins, rehypePlugins } from '../../utils/markdownStyles.jsx';
import { COLORS } from '../../styles/tokens';

const { Text, Paragraph } = Typography;

function ChunkTab({ chunk }) {
  return (
    <Card
      title={
        <Space>
          <FileTextOutlined style={{ color: COLORS.success }} />
          <Text strong style={{ fontSize: 16 }}>Top {chunk.order}</Text>
          <Tag color="green">分块</Tag>
        </Space>
      }
      extra={
        <Space>
          <Text type="secondary">{chunk.filename}</Text>
          {typeof chunk.score === 'number' && (
            <Tag color="blue">{(chunk.score * 100).toFixed(0)}%</Tag>
          )}
        </Space>
      }
      bordered={false}
      style={{
        height: '100%',
        borderRadius: 0,
        boxShadow: 'none',
      }}
      bodyStyle={{
        padding: '24px',
        height: 'calc(100% - 60px)',
        overflow: 'auto',
      }}
    >
      {chunk.content ? (
        <div style={{
          padding: '20px',
          backgroundColor: COLORS.bgCard,
          borderRadius: '8px',
        }}>
          <ReactMarkdown
            remarkPlugins={remarkPlugins}
            rehypePlugins={rehypePlugins}
          >
            {chunk.content}
          </ReactMarkdown>
        </div>
      ) : (
        <Empty
          description={
            <Space direction="vertical" size="small">
              <Paragraph type="secondary">分块内容为空</Paragraph>
            </Space>
          }
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ marginTop: 80 }}
        />
      )}
    </Card>
  );
}

export default ChunkTab;
