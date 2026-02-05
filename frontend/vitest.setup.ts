import "@testing-library/jest-dom";
import { config } from "dotenv";
import { beforeEach, vi } from "vitest";

// Load environment variables from .env file for tests
config();

// Mock localStorage for tests
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem(key: string) {
      return store[key] || null;
    },
    setItem(key: string, value: string) {
      store[key] = value.toString();
    },
    removeItem(key: string) {
      delete store[key];
    },
    clear() {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key(index: number) {
      const keys = Object.keys(store);
      return keys[index] || null;
    },
  };
})();

beforeEach(() => {
  localStorageMock.clear();
  global.localStorage = localStorageMock as Storage;
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
  });
});
