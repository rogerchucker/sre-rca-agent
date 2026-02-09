import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type IncidentTab = {
  id: string;
  title: string;
  severity: string;
  environment: string;
  subject: string;
};

type IncidentTabsState = {
  openTabs: IncidentTab[];
  activeTabId: string | null;
};

const STORAGE_KEY = 'incident-tabs-v1';
const MAX_TABS = 5;

function loadState(): IncidentTabsState {
  if (!browser) return { openTabs: [], activeTabId: null };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { openTabs: [], activeTabId: null };
    const parsed = JSON.parse(raw) as IncidentTabsState;
    if (!Array.isArray(parsed.openTabs)) {
      return { openTabs: [], activeTabId: null };
    }
    return {
      openTabs: parsed.openTabs.slice(0, MAX_TABS),
      activeTabId: parsed.activeTabId ?? null
    };
  } catch {
    return { openTabs: [], activeTabId: null };
  }
}

function persist(state: IncidentTabsState) {
  if (!browser) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

const initialState = loadState();

const { subscribe, update, set } = writable<IncidentTabsState>(initialState);

function openTab(tab: IncidentTab) {
  update((state) => {
    const existing = state.openTabs.find((t) => t.id === tab.id);
    let nextTabs = state.openTabs.filter((t) => t.id !== tab.id);
    nextTabs = [tab, ...nextTabs];
    if (nextTabs.length > MAX_TABS) {
      nextTabs = nextTabs.slice(0, MAX_TABS);
    }
    const nextState = {
      openTabs: nextTabs,
      activeTabId: tab.id
    };
    persist(nextState);
    return nextState;
  });
}

function closeTab(id: string) {
  update((state) => {
    const nextTabs = state.openTabs.filter((t) => t.id !== id);
    let nextActive = state.activeTabId;
    if (state.activeTabId === id) {
      nextActive = nextTabs.length > 0 ? nextTabs[0].id : null;
    }
    const nextState = { openTabs: nextTabs, activeTabId: nextActive };
    persist(nextState);
    return nextState;
  });
}

function setActive(id: string) {
  update((state) => {
    const nextState = { ...state, activeTabId: id };
    persist(nextState);
    return nextState;
  });
}

function syncFromRoute(id: string) {
  update((state) => {
    if (!id) return state;
    const exists = state.openTabs.some((t) => t.id === id);
    const nextState = { ...state, activeTabId: id };
    if (!exists) {
      return state;
    }
    persist(nextState);
    return nextState;
  });
}

function reset() {
  const nextState = { openTabs: [], activeTabId: null };
  set(nextState);
  persist(nextState);
}

export const incidentTabs = {
  subscribe,
  openTab,
  closeTab,
  setActive,
  syncFromRoute,
  reset,
  maxTabs: MAX_TABS
};
