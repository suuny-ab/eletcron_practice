import { Typography, Empty, Space, Tabs } from 'antd';
import NoteTab from './NoteTab';
import ChunkTab from './ChunkTab';
import { COLORS } from '../../styles/tokens';

const { Text, Paragraph } = Typography;

function NoteEditor({
  activeTab,
  onTabChange,
  onTabClose,
  openNotes,
  openChunks,
  noteStates,
  noteDefaults,
  configTabVisible,
  configTabContent,
  onStartEdit,
  onCancelEdit,
  onSave,
  onNoteStateChange,
}) {
  const getNoteState = (noteKey) => noteStates[noteKey] || noteDefaults;

  const noteTabs = openNotes.map(note => ({
    key: `note:${note.key}`,
    label: note.title || note.key,
    closable: true,
    children: (
      <NoteTab
        noteKey={note.key}
        noteTitle={note.title || note.key}
        noteState={getNoteState(note.key)}
        onStartEdit={onStartEdit}
        onCancelEdit={onCancelEdit}
        onSave={onSave}
        onNoteStateChange={onNoteStateChange}
      />
    ),
  }));

  const chunkTabs = openChunks.map(chunk => ({
    key: chunk.key,
    label: chunk.title,
    closable: true,
    children: <ChunkTab chunk={chunk} />,
  }));

  const contentTabs = [...noteTabs, ...chunkTabs];
  const hasContentTabs = contentTabs.length > 0;

  const tabItems = [
    ...(hasContentTabs ? contentTabs : [{
      key: 'notes',
      label: '笔记',
      closable: false,
      children: (
        <Empty
          description={
            <Space direction="vertical" size="small">
              <Paragraph type="secondary">请在左侧文件树中选择文件</Paragraph>
              <Text type="secondary" style={{ fontSize: 12 }}>
                仅支持预览和编辑 Markdown 格式文件
              </Text>
            </Space>
          }
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ marginTop: 80 }}
        />
      )
    }]),
    ...(configTabVisible && configTabContent ? [
      {
        key: 'config',
        label: '系统配置',
        closable: true,
        children: configTabContent,
      }
    ] : [])
  ];

  const handleEdit = (targetKey, action) => {
    if (action === 'remove') {
      onTabClose(targetKey);
    }
  };

  return (
    <div style={{
      height: '100%',
      padding: '0',
      background: COLORS.bgBase,
    }}>
      <Tabs
        className="knowledge-tabs"
        type="editable-card"
        hideAdd
        activeKey={activeTab}
        onChange={onTabChange}
        onEdit={handleEdit}
        items={tabItems}
        tabBarStyle={{
          margin: 0,
          padding: '0 16px',
          background: COLORS.bgCard,
          borderBottom: `1px solid ${COLORS.borderLight}`,
        }}
        style={{ height: '100%' }}
      />
      <style>{`
        .knowledge-tabs {
          height: 100%;
          display: flex;
          flex-direction: column;
        }
        .knowledge-tabs .ant-tabs-content-holder {
          flex: 1;
          min-height: 0;
        }
        .knowledge-tabs .ant-tabs-content,
        .knowledge-tabs .ant-tabs-tabpane {
          height: 100%;
        }
      `}</style>
    </div>
  );
}

export default NoteEditor;
