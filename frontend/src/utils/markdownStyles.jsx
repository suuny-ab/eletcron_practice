import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';

export const remarkPlugins = [remarkGfm];
export const rehypePlugins = [rehypeHighlight, rehypeRaw];

const sizePresets = {
  full: {
    h1: { fontSize: '2em', marginTop: '1.5em', marginBottom: '0.8em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' },
    h2: { fontSize: '1.5em', marginTop: '1.5em', marginBottom: '0.8em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' },
    h3: { fontSize: '1.25em', marginTop: '1.5em', marginBottom: '0.8em' },
    p: { lineHeight: '1.8', marginBottom: '1em', color: '#24292e' },
    ul: { paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' },
    ol: { paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' },
    li: { marginBottom: '0.5em' },
    inlineCode: { padding: '0.2em 0.4em', fontSize: '85%' },
    pre: { padding: '16px', borderRadius: '6px', marginBottom: '1em' },
    blockquote: { borderLeftWidth: '4px', padding: '0 1em', marginBottom: '1em' },
  },
  preview: {
    h1: { fontSize: '1.8em', marginTop: '1.2em', marginBottom: '0.6em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' },
    h2: { fontSize: '1.4em', marginTop: '1.2em', marginBottom: '0.6em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' },
    h3: { fontSize: '1.2em', marginTop: '1.2em', marginBottom: '0.6em' },
    p: { lineHeight: '1.8', marginBottom: '1em', color: '#24292e' },
    ul: { paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' },
    ol: { paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' },
    li: { marginBottom: '0.5em' },
    inlineCode: { padding: '0.2em 0.4em', fontSize: '85%' },
    pre: { padding: '12px', borderRadius: '6px', marginBottom: '1em' },
    blockquote: { borderLeftWidth: '4px', padding: '0 1em', marginBottom: '1em' },
  },
  compact: {
    h1: { fontSize: '1.5em', marginTop: '0.8em', marginBottom: '0.4em' },
    h2: { fontSize: '1.3em', marginTop: '0.8em', marginBottom: '0.4em' },
    h3: { fontSize: '1.1em', marginTop: '0.6em', marginBottom: '0.3em' },
    p: { margin: '0.4em 0' },
    ul: { paddingLeft: '1.5em', margin: '0.4em 0' },
    ol: { paddingLeft: '1.5em', margin: '0.4em 0' },
    li: { marginBottom: '0.2em' },
    inlineCode: { padding: '0.1em 0.3em', fontSize: '0.9em' },
    pre: { padding: '8px', borderRadius: '4px', margin: '0.4em 0', fontSize: '12px' },
    blockquote: { borderLeftWidth: '3px', padding: '0 0.8em', margin: '0.4em 0', fontSize: '0.95em' },
  },
};

export function createMarkdownComponents(size = 'full') {
  const s = sizePresets[size] || sizePresets.full;
  const hasTableSupport = size === 'full' || size === 'preview';

  const components = {
    h1: ({ children }) => <h1 style={{ ...s.h1, fontWeight: 'bold' }}>{children}</h1>,
    h2: ({ children }) => <h2 style={{ ...s.h2, fontWeight: 'bold' }}>{children}</h2>,
    h3: ({ children }) => <h3 style={{ ...s.h3, fontWeight: 'bold' }}>{children}</h3>,
    p: ({ children }) => <p style={s.p}>{children}</p>,
    ul: ({ children }) => <ul style={s.ul}>{children}</ul>,
    ol: ({ children }) => <ol style={s.ol}>{children}</ol>,
    li: ({ children }) => <li style={s.li}>{children}</li>,
    code: ({ inline, className, children, ...props }) => {
      if (inline) {
        return (
          <code
            style={{
              backgroundColor: 'rgba(27, 31, 35, 0.05)',
              ...s.inlineCode,
              borderRadius: '3px',
              fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
            }}
            {...props}
          >
            {children}
          </code>
        );
      }
      return <code className={className} {...props}>{children}</code>;
    },
    pre: ({ children }) => (
      <pre
        style={{
          backgroundColor: '#ffffff',
          ...s.pre,
          overflow: 'auto',
          border: '1px solid #e8e8e8',
        }}
      >
        {children}
      </pre>
    ),
    blockquote: ({ children }) => (
      <blockquote
        style={{
          borderLeft: `${s.blockquote.borderLeftWidth} solid #dfe2e5`,
          padding: s.blockquote.padding,
          color: '#6a737d',
          marginLeft: '0',
          marginBottom: s.blockquote.marginBottom,
          margin: s.blockquote.margin,
          fontSize: s.blockquote.fontSize,
        }}
      >
        {children}
      </blockquote>
    ),
    a: ({ children, href }) => <a href={href} style={{ color: '#0366d6', textDecoration: 'none' }}>{children}</a>,
  };

  if (hasTableSupport) {
    components.table = ({ children }) => (
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1em' }}>{children}</table>
    );
    components.thead = ({ children }) => <thead>{children}</thead>;
    components.tbody = ({ children }) => <tbody>{children}</tbody>;
    components.tr = ({ children }) => <tr style={{ borderBottom: '1px solid #eaecef' }}>{children}</tr>;
    components.th = ({ children }) => (
      <th style={{ padding: '6px 13px', fontWeight: '600', borderBottom: '1px solid #dfe2e5', backgroundColor: '#f6f8fa', textAlign: 'left' }}>
        {children}
      </th>
    );
    components.td = ({ children }) => (
      <td style={{ padding: '6px 13px', borderBottom: '1px solid #eaecef', textAlign: 'left' }}>{children}</td>
    );
  }

  return components;
}
