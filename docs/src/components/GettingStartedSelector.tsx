'use client'

import { Combobox, Listbox } from '@headlessui/react'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/20/solid'
import clsx from 'clsx'

import Image from 'next/image'
import {
  createContext,
  Dispatch,
  SetStateAction,
  useEffect,
  useRef,
  useState,
} from 'react'

type CloudPrvider = {
  name: string
  avatar: string
}

const cloudProviders = [
  { name: 'AWS', avatar: '/images/aws.svg' },
  { name: 'GCP', avatar: '/images/gcp.svg' },
]

type GettingStartedSelectorProps = {
  // awsRuntimeOptions: string[]
  // gcpRuntimeOptions: string[]
  children: React.ReactNode
}

interface GettingStartedContextType {
  selectedCloudProvider: CloudPrvider
  setSelectedCloudProvider: Dispatch<SetStateAction<CloudPrvider>>
}

export const GettingStartedContext = createContext<GettingStartedContextType>({
  selectedCloudProvider: cloudProviders[0],
  setSelectedCloudProvider: () => {},
})

function Selector({
  selected,
  setSelected,
  options,
}: {
  selected: CloudPrvider
  setSelected: (item: CloudPrvider) => void
  options: CloudPrvider[]
}) {
  return (
    <Listbox value={selected} onChange={setSelected}>
      <div className="relative max-w-32">
        <Listbox.Button className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-primary sm:text-sm sm:leading-6">
          <span className="flex items-center">
            <Image
              height={500}
              width={500}
              alt=""
              src={selected.avatar}
              className="h-5 w-5 flex-shrink-0 rounded-full"
            />
            <span className="ml-3 block truncate">{selected.name}</span>
          </span>
          <span className="pointer-events-none absolute inset-y-0 right-0 ml-3 flex items-center pr-2">
            <ChevronUpDownIcon
              aria-hidden="true"
              className="h-5 w-5 text-gray-400"
            />
          </span>
        </Listbox.Button>

        <Listbox.Options className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none data-[closed]:data-[leave]:opacity-0 data-[leave]:transition data-[leave]:duration-100 data-[leave]:ease-in sm:text-sm">
          {options.map((option) => (
            <Listbox.Option
              key={option.name}
              value={option}
              className="group relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 hover:bg-primary/70 hover:text-white"
            >
              <div className="flex items-center">
                <img
                  alt=""
                  src={option.avatar}
                  className="h-5 w-5 flex-shrink-0 rounded-full"
                />
                <span
                  className={clsx(
                    'ml-3 block truncate font-normal',
                    option.name == selected.name
                      ? 'font-semibold'
                      : 'font-normal',
                  )}
                >
                  {option.name}
                </span>
              </div>

              {option.name == selected.name && (
                <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-primary">
                  <CheckIcon aria-hidden="true" className="h-5 w-5" />
                </span>
              )}
            </Listbox.Option>
          ))}
        </Listbox.Options>
      </div>
    </Listbox>
  )
}

export function GettingStartedSelector({
  // awsRuntimeOptions,
  // gcpRuntimeOptions,
  children,
}: GettingStartedSelectorProps) {
  const [selectedCloudProvider, setSelectedCloudProvider] = useState(
    cloudProviders[0],
  )

  return (
    <GettingStartedContext.Provider
      value={{ selectedCloudProvider, setSelectedCloudProvider }}
    >
      <div className="not-prose sticky top-[93px] z-10  w-full rounded-md bg-transparent p-1 py-2 ring-1 ring-inset backdrop-blur md:top-[109px]">
        <Selector
          selected={selectedCloudProvider}
          setSelected={setSelectedCloudProvider}
          options={cloudProviders}
        />
      </div>
      {children}
    </GettingStartedContext.Provider>
  )
}
