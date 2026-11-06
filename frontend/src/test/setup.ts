import '@testing-library/jest-dom/vitest';

// React Flow (FE-04) expects these browser APIs that jsdom lacks.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as Record<string, unknown>).ResizeObserver =
  (globalThis as Record<string, unknown>).ResizeObserver ?? ResizeObserverMock;

if (typeof (globalThis as Record<string, unknown>).DOMMatrixReadOnly === 'undefined') {
  class DOMMatrixReadOnlyMock {
    constructor(public transform?: string) {}
    scale() {
      return this;
    }
    translate() {
      return this;
    }
    inverse() {
      return this;
    }
  }
  (globalThis as Record<string, unknown>).DOMMatrixReadOnly = DOMMatrixReadOnlyMock;
}
