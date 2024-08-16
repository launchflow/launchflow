"use client"
import React from 'react';
import { TabContext } from '@/components/TabProvider'; // Import the context


type TabsProps = {
    label: string;
    children: React.ReactNode;

}

export function Tab({ label, children }: TabsProps) {
    const currentTab = React.useContext(TabContext);

    if (label !== currentTab.currentTab) {
        return null;
    }

    return children;
}
