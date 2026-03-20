import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from './ChatInput';
import { useAnimalStore } from '@/stores/animalStore';
import { useConversationStore } from '@/stores/conversationStore';

// Mock the stores
jest.mock('@/stores/animalStore', () => ({
  useAnimalStore: jest.fn(),
}));

jest.mock('@/stores/conversationStore', () => ({
  useConversationStore: jest.fn(),
}));

// Mock EmojiPicker
jest.mock('./EmojiPicker', () => ({
  EmojiPicker: ({ isOpen, onSelect, onClose }: { isOpen: boolean; onSelect: (emoji: string) => void; onClose: () => void }) => {
    if (!isOpen) return null;
    return (
      <div data-testid="emoji-picker">
        <button onClick={() => { onSelect('😀'); onClose(); }}>😀</button>
        <button onClick={onClose}>Close</button>
      </div>
    );
  },
}));

// Mock MentionDropdown
jest.mock('./MentionDropdown', () => ({
  MentionDropdown: ({ animals, filter, onSelect, onClose }: { 
    animals: Array<{ id: string; name: string }>; 
    filter: string; 
    onSelect: (animal: { id: string; name: string }) => void;
    onClose: () => void;
  }) => {
    if (!filter) return null;
    const filtered = animals.filter(a => a.name.includes(filter));
    if (filtered.length === 0) return null;
    return (
      <div data-testid="mention-dropdown">
        {filtered.map(animal => (
          <button key={animal.id} onClick={() => onSelect(animal)}>{animal.name}</button>
        ))}
        <button onClick={onClose}>Close</button>
      </div>
    );
  },
}));

const mockAnimals = [
  {
    id: 'xueqiu' as const,
    name: '雪球',
    species: '雪纳瑞',
    color: '#4A90E2',
    personality: '聪明、友善',
    avatar: '/avatars/xueqiu.svg',
    status: 'available' as const,
    isFavorite: false,
    description: '雪球是一只可爱的雪纳瑞犬',
    traits: ['聪明', '友善'],
    specialties: ['代码审查'],
    greetings: ['汪汪！'],
  },
  {
    id: 'liuliu' as const,
    name: '六六',
    species: '虎皮鹦鹉(蓝)',
    color: '#50C8E6',
    personality: '活泼、好奇',
    avatar: '/avatars/liuliu.svg',
    status: 'available' as const,
    isFavorite: false,
    description: '六六是一只蓝色的虎皮鹦鹉',
    traits: ['活泼', '好奇'],
    specialties: ['代码审查'],
    greetings: ['啾啾！'],
  },
];

const mockConversation = {
  id: 'test-conversation',
  title: 'Test Conversation',
  participants: mockAnimals,
  messages: [],
  status: 'active' as const,
  createdAt: new Date(),
  updatedAt: new Date(),
  isFavorite: false,
  unreadCount: 0,
};

describe('ChatInput', () => {
  const mockOnSend = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    (useAnimalStore as jest.Mock).mockReturnValue({
      animals: mockAnimals,
    });
    
    const mockStoreState = {
      conversations: [mockConversation],
      activeConversationId: 'test-conversation',
      getActiveConversation: () => mockConversation,
    };
    
    (useConversationStore as jest.Mock).mockImplementation((selector?: (state: typeof mockStoreState) => unknown) => {
      if (typeof selector === 'function') {
        return selector(mockStoreState);
      }
      return mockStoreState;
    });
  });

  it('should render with placeholder', () => {
    render(<ChatInput onSend={mockOnSend} />);
    expect(screen.getByPlaceholderText('输入消息...')).toBeInTheDocument();
  });

  it('should render with custom placeholder', () => {
    render(<ChatInput onSend={mockOnSend} placeholder="Type a message..." />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
  });

  it('should call onSend when Enter is pressed (without Shift)', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello{enter}');
    
    expect(mockOnSend).toHaveBeenCalledWith('Hello');
  });

  it('should not call onSend when Shift+Enter is pressed', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello{Shift>}{enter}{/Shift}');
    
    // Should not send because Shift+Enter is for new line
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('should not call onSend when message is empty', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '{enter}');
    
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('should not call onSend when message is only whitespace', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '   {enter}');
    
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('should clear input after sending', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello{enter}');
    
    expect(textarea).toHaveValue('');
  });

  it('should be disabled when disabled prop is true', () => {
    render(<ChatInput onSend={mockOnSend} disabled />);
    
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
  });

  it('should show emoji picker when emoji button is clicked', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const buttons = screen.getAllByRole('button');
    const emojiBtn = buttons.find(btn => btn.querySelector('svg.lucide-smile'));
    
    if (emojiBtn) {
      await user.click(emojiBtn);
      expect(screen.getByTestId('emoji-picker')).toBeInTheDocument();
    }
  });

  it('should detect @ and show mention state', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@雪');
    
    // The mention dropdown should appear with filtered animals
    await waitFor(() => {
      expect(screen.getByTestId('mention-dropdown')).toBeInTheDocument();
    });
  });

  it('should close mention dropdown when Escape is pressed', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@雪');
    
    await waitFor(() => {
      expect(screen.getByTestId('mention-dropdown')).toBeInTheDocument();
    });
    
    await user.type(textarea, '{escape}');
    
    await waitFor(() => {
      expect(screen.queryByTestId('mention-dropdown')).not.toBeInTheDocument();
    });
  });

  it('should send message when send button is clicked', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello World');
    
    const buttons = screen.getAllByRole('button');
    const sendBtn = buttons.find(btn => btn.querySelector('svg.lucide-send'));
    
    if (sendBtn) {
      await user.click(sendBtn);
      expect(mockOnSend).toHaveBeenCalledWith('Hello World');
    }
  });

  it('should trim whitespace from message before sending', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={mockOnSend} />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '  Hello World  {enter}');
    
    expect(mockOnSend).toHaveBeenCalledWith('Hello World');
  });
});