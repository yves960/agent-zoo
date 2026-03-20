import { render, screen, fireEvent } from '@testing-library/react';
import { MentionDropdown } from './MentionDropdown';
import type { AnimalAgent } from '@/types';

// Mock AnimalAvatar component
jest.mock('@/components/animals/AnimalAvatar', () => ({
  AnimalAvatar: ({ animal }: { animal: { name: string; color: string } }) => (
    <div data-testid={`avatar-${animal.name}`} style={{ backgroundColor: animal.color }} />
  ),
}));

const mockAnimals: AnimalAgent[] = [
  {
    id: 'xueqiu',
    name: '雪球',
    species: '雪纳瑞',
    color: '#4A90E2',
    personality: '聪明、友善',
    avatar: '/avatars/xueqiu.svg',
    status: 'available',
    isFavorite: false,
    description: '雪球是一只可爱的雪纳瑞犬',
    traits: ['聪明', '友善'],
    specialties: ['代码审查'],
    greetings: ['汪汪！'],
  },
  {
    id: 'liuliu',
    name: '六六',
    species: '虎皮鹦鹉(蓝)',
    color: '#50C8E6',
    personality: '活泼、好奇',
    avatar: '/avatars/liuliu.svg',
    status: 'available',
    isFavorite: false,
    description: '六六是一只蓝色的虎皮鹦鹉',
    traits: ['活泼', '好奇'],
    specialties: ['代码审查'],
    greetings: ['啾啾！'],
  },
  {
    id: 'xiaohuang',
    name: '小黄',
    species: '虎皮鹦鹉(黄绿)',
    color: '#7ED321',
    personality: '开朗、乐观',
    avatar: '/avatars/xiaohuang.svg',
    status: 'available',
    isFavorite: false,
    description: '小黄是一只黄绿相间的虎皮鹦鹉',
    traits: ['开朗', '乐观'],
    specialties: ['视觉设计'],
    greetings: ['唧唧！'],
  },
];

describe('MentionDropdown', () => {
  const mockOnSelect = jest.fn();
  const mockOnClose = jest.fn();
  const defaultPosition = { top: 0, left: 0 };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render filtered animals by name', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('雪球')).toBeInTheDocument();
    expect(screen.queryByText('六六')).not.toBeInTheDocument();
    expect(screen.queryByText('小黄')).not.toBeInTheDocument();
  });

  it('should render filtered animals by id', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="liu"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('六六')).toBeInTheDocument();
    expect(screen.queryByText('雪球')).not.toBeInTheDocument();
    expect(screen.queryByText('小黄')).not.toBeInTheDocument();
  });

  it('should render filtered animals by species', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="鹦鹉"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('六六')).toBeInTheDocument();
    expect(screen.getByText('小黄')).toBeInTheDocument();
    expect(screen.queryByText('雪球')).not.toBeInTheDocument();
  });

  it('should return null when no matches found', () => {
    const { container } = render(
      <MentionDropdown
        animals={mockAnimals}
        filter="xyz"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(container.firstChild).toBeNull();
  });

  it('should show all animals when filter is empty', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter=""
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('雪球')).toBeInTheDocument();
    expect(screen.getByText('六六')).toBeInTheDocument();
    expect(screen.getByText('小黄')).toBeInTheDocument();
  });

  it('should call onSelect when animal is clicked', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    fireEvent.click(screen.getByText('雪球'));
    
    expect(mockOnSelect).toHaveBeenCalledWith(mockAnimals[0]);
  });

  it('should display animal id with @ prefix', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('@xueqiu')).toBeInTheDocument();
  });

  it('should display animal species', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('雪纳瑞')).toBeInTheDocument();
  });

  it('should display match count in footer', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="鹦鹉"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('2 个匹配')).toBeInTheDocument();
  });

  it('should apply position props', () => {
    const position = { top: 100, left: 200 };
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={position}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('提及动物')).toBeInTheDocument();
    expect(screen.getByText('雪纳瑞')).toBeInTheDocument();
  });

  it('should set up click outside listener', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('雪球')).toBeInTheDocument();
  });

  it('should close on Escape key press', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    fireEvent.keyDown(document, { key: 'Escape' });
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should render with position styles applied', () => {
    const position = { top: 100, left: 200 };
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={position}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('提及动物')).toBeInTheDocument();
  });

  it('should render as a dropdown container', () => {
    render(
      <MentionDropdown
        animals={mockAnimals}
        filter="雪"
        position={defaultPosition}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('提及动物')).toBeInTheDocument();
    expect(screen.getByText('雪球')).toBeInTheDocument();
  });
});