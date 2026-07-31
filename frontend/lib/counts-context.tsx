"use client";

import { createContext, useContext } from "react";

export const CountsContext = createContext<{ refresh: () => void }>({
  refresh: () => {},
});

export function useCountsRefresh() {
  return useContext(CountsContext).refresh;
}
