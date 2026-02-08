import { render, screen, waitFor } from '@testing-library/react';
import { ChatContainer } from '../ChatContainer';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch
global.fetch = vi.fn();

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

type MockFetch = ReturnType<typeof vi.fn>;

describe('ChatContainer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    (global.fetch as MockFetch).mockResolvedValueOnce({
      json: async () => ({ messages: [] }),
    });

    render(<ChatContainer />);
    expect(screen.getByText(/No messages yet/i)).toBeInTheDocument();
  });

  it('fetches messages on mount', async () => {
    const mockMessages = [
      {
        id: '1',
        role: 'user',
        content: 'Hello',
        messageType: 'text',
        createdAt: Date.now(),
      },
    ];

    (global.fetch as MockFetch).mockResolvedValueOnce({
      json: async () => ({ messages: mockMessages }),
    });

    render(<ChatContainer />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/chat/messages');
    });
  });
});
