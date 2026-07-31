"use client";

import { createContext, useContext } from "react";

export const SearchContext = createContext<string>("");

export function usePageSearch() {
  return useContext(SearchContext);
}
