import { memo } from 'react';
import { Typography } from 'antd';
import ReactMarkdown from 'react-markdown';
import { remarkPlugins, rehypePlugins, createMarkdownComponents } from '../../utils/markdownStyles.jsx';
import { COLORS } from '../../styles/tokens';

const { Text, Paragraph } = Typography;

const ChatMessage = memo(function ChatMessage({ msg, isRagMode }) {
  const isUser = msg.role === 'user';
  return (
    <div
      style={{
        padding: '12px',
        borderRadius: '8px',
        background: isUser
          ? (isRagMode ? `${COLORS.rag}0a` : COLORS.bgActive)
          : COLORS.bgHover,
        maxWidth: '85%',
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        borderLeft: !isUser && isRagMode ? `3px solid ${COLORS.ragLight}` : undefined,
      }}
    >
      <Text strong style={{
        display: 'block',
        marginBottom: '4px',
        fontSize: 12,
        color: isRagMode && !isUser ? COLORS.rag : undefined,
      }}>
        {isUser ? '用户' : 'AI'}
      </Text>
      {msg.role === 'assistant' ? (
        <div style={{ fontSize: 13, lineHeight: '1.6' }}>
          <ReactMarkdown
            remarkPlugins={remarkPlugins}
            rehypePlugins={rehypePlugins}
            components={createMarkdownComponents('compact')}
          >
            {msg.content}
          </ReactMarkdown>
        </div>
      ) : (
        <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13 }}>
          {msg.content}
        </Paragraph>
      )}
    </div>
  );
});

export default ChatMessage;
