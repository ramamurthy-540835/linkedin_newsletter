'use client';
import { createContext, useContext } from 'react';

const DraftCartContext = createContext(null);
export default DraftCartContext;
export function useDraftCart() { return useContext(DraftCartContext); }
