"use client"
import React, { useState, createContext, Dispatch, SetStateAction } from 'react';

interface TabContextType {
    currentTab: string;
    setCurrentTab: Dispatch<SetStateAction<string>>;
}

export const TabContext = createContext<TabContextType>({
    currentTab: 'unset',
    setCurrentTab: () => { },
});

type TabProviderProps = {
    defaultLabel: string;
    children: React.ReactNode;
};

// Provider component
export function TabProvider({ defaultLabel, children }: TabProviderProps) {
    const [currentTab, setCurrentTab] = useState(defaultLabel);

    return (
        <TabContext.Provider value={{ currentTab, setCurrentTab }}>
            {children}
        </TabContext.Provider>
    );
};
