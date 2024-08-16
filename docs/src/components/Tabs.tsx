'use client'
import React, { useContext } from 'react'

import { TabContext } from '@/components/TabProvider' // Import the context

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

type TabsProps = {
  labels: string[]
  children: React.ReactNode
}

export function Tabs({ labels, children }: TabsProps) {
  const { currentTab, setCurrentTab } = useContext(TabContext)

  return (
    <div>
      <div>
        {/* <div className="sm:hidden">
                    <label htmlFor="tabs" className="sr-only">
                        Select a tab
                    </label>
                    <select
                        id="tabs"
                        name="tabs"
                        className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm dark:bg-background_dark dark:ring-1 dark:ring-slate-300/10"
                        defaultValue={currentTab}
                        onChange={(e) => setCurrentTab(e.target.value)}
                    >
                        {labels.map((label) => (
                            <option key={label} value={label}>{label}</option>
                        ))}
                    </select>
                </div> */}
        <div className="overflow-x-auto">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8" aria-label="Tabs">
              {labels.map((label) => (
                <button
                  key={label}
                  onClick={() => setCurrentTab(label)}
                  className={classNames(
                    label === currentTab
                      ? 'border-logo text-logo dark:border-secondary dark:text-secondary'
                      : 'border-transparent text-gray-500 hover:border-logo hover:text-logo dark:text-gray-200 dark:hover:border-secondary dark:hover:text-secondary',
                    'whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium',
                  )}
                  aria-current={label === currentTab ? 'page' : undefined}
                >
                  {label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </div>
      {children}
    </div>
  )
}
