import { test, expect, chromium, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8001';

test.describe('Agent Zoo E2E Tests', () => {
  
  test('homepage loads correctly', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('text=Agent动物园')).toBeVisible();
    await expect(page.locator('text=Zoo Multi-Agent')).toBeVisible();
  });

  test('agents are loaded from API', async ({ page }) => {
    const response = await page.request.get(`${API_URL}/api/animals`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.animals).toBeDefined();
    
    const animalIds = Object.keys(data.animals);
    console.log('Loaded animals:', animalIds);
    expect(animalIds.length).toBeGreaterThan(0);
  });

  test('WebSocket connects after page load', async ({ page }) => {
    const wsConnections: string[] = [];
    
    page.on('websocket', (ws) => {
      wsConnections.push(ws.url());
      console.log('WebSocket connected:', ws.url());
    });
    
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    console.log('All WebSocket connections:', wsConnections);
    
    const hasWsConnection = wsConnections.some(url => url.includes('8001'));
    expect(hasWsConnection).toBeTruthy();
  });

  test('new conversation button works', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    
    const sidebarNewChatBtn = page.getByRole('button', { name: '新对话', exact: true });
    await sidebarNewChatBtn.click();
    await page.waitForTimeout(500);
    
    const welcomeOrInput = page.locator('text=欢迎来到Agent动物园').or(page.locator('input'));
    await expect(welcomeOrInput.first()).toBeVisible();
  });

  test('can type and send message via WebSocket', async ({ page }) => {
    const wsMessages: any[] = [];
    
    page.on('websocket', (ws) => {
      ws.on('framesent', (data) => {
        wsMessages.push({ direction: 'sent', data: data.payload });
      });
      ws.on('framereceived', (data) => {
        wsMessages.push({ direction: 'received', data: data.payload });
      });
    });
    
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    const sidebarNewChatBtn = page.getByRole('button', { name: '新对话', exact: true });
    await sidebarNewChatBtn.click();
    await page.waitForTimeout(500);
    
    const inputField = page.locator('input').first();
    await inputField.fill('大家好呀');
    await inputField.press('Enter');
    
    await page.waitForTimeout(3000);
    
    console.log('WebSocket messages:', wsMessages.length);
    wsMessages.forEach((m, i) => {
      console.log('Message ' + i + ':', m.direction, m.data?.substring(0, 200));
    });
    
    const userMessage = page.locator('text=大家好呀');
    const isVisible = await userMessage.first().isVisible().catch(() => false);
    console.log('User message visible:', isVisible);
    
    await page.screenshot({ path: 'chat-result.png', fullPage: true });
    console.log('Screenshot saved to chat-result.png');
  });
});

test.describe('Debug Tests', () => {
  
  test('debug WebSocket message flow', async ({ page }) => {
    const logs: any[] = [];
    const apiCalls: any[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        logs.push({ type: 'error', text: msg.text() });
      }
    });
    
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        apiCalls.push({ url: response.url(), status: response.status() });
      }
    });
    
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    console.log('API calls:', apiCalls);
    console.log('Console errors:', logs);
    
    const newChatBtn = page.locator('button').filter({ hasText: '新对话' }).first();
    await newChatBtn.click();
    await page.waitForTimeout(1000);
    
    const input = page.locator('input').first();
    await input.fill('测试消息');
    await input.press('Enter');
    
    await page.waitForTimeout(5000);
    
    const messages = await page.locator('[class*="message"]').count();
    console.log('Message elements found:', messages);
    
    await page.screenshot({ path: 'debug-result.png', fullPage: true });
  });
});
