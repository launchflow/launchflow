import clsx from 'clsx'
import Image from 'next/image'
import { Fragment, useState } from 'react'

import { Button } from '@/components/Button'
import { HeroBackground } from '@/components/HeroBackground'
import blurCyanImage from '@/images/blur-cyan.png'
import blurIndigoImage from '@/images/blur-indigo.png'

import { HeroCode } from './HeroCode'

const awsCode = `from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f"Hello from {lf.environment}!"

# Deploy this FastAPI app to ECS Fargate on AWS
api = lf.aws.ECSFargateService("my-api", domain="launchflow.com")`

const gcpCode = `from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f"Hello from {lf.environment}!"

# Deploy this FastAPI app to Cloud Run on GCP
api = lf.gcp.CloudRunService("my-api", domain="launchflow.com")`

const tabs = [
  { name: 'aws.py', isActive: true, code: awsCode },
  { name: 'gcp.py', isActive: false, code: gcpCode },
]

function TrafficLightsIcon(props: React.ComponentPropsWithoutRef<'svg'>) {
  return (
    <svg aria-hidden="true" viewBox="0 0 42 10" fill="none" {...props}>
      <circle cx="5" cy="5" r="4.5" />
      <circle cx="21" cy="5" r="4.5" />
      <circle cx="37" cy="5" r="4.5" />
    </svg>
  )
}

export function Hero() {
  const [currentTab, setCurrentTab] = useState(tabs[0])
  function toggleTable(tab: (typeof tabs)[0]) {
    setCurrentTab(tab)
    tab.isActive = true
    for (let t of tabs) {
      if (t.name !== tab.name) {
        t.isActive = false
      }
    }
  }

  return (
    <div className="overflow-hidden bg-background_dark dark:-mb-32 dark:mt-[-4.75rem] dark:pb-32 dark:pt-[4.75rem]">
      <div className="py-16 sm:px-2 lg:relative lg:px-0 lg:py-20">
        <div className="mx-auto grid max-w-2xl grid-cols-1 items-center gap-x-8 gap-y-16 px-4 lg:max-w-8xl lg:grid-cols-2 lg:px-8 xl:gap-x-16 xl:px-12">
          <div className="relative z-10 md:text-center lg:text-left">
            <Image
              className="absolute bottom-full right-full -mb-56 -mr-72 opacity-50"
              src={blurCyanImage}
              alt=""
              width={530}
              height={530}
              unoptimized
              priority
            />
            <div className="relative">
              <p className="fluid-text inline bg-gradient-to-r from-primary via-secondary to-logo bg-clip-text font-display tracking-tight text-transparent ">
                LaunchFlow Docs
              </p>
              <p className="mt-3 text-lg tracking-tight text-slate-300 sm:text-2xl">
                Deploy applications to AWS and GCP with Python.
                <br className="hidden sm:block" /> No messy YAML required.
              </p>
              <div className="mt-8 flex items-center gap-4 md:justify-center lg:justify-start">
                <Button variant="primary-lg" href="/docs/get-started">
                  Get Started
                </Button>
              </div>
            </div>
          </div>
          <div className="relative lg:static xl:pl-10">
            <div className="absolute inset-x-[-50vw] -bottom-48 -top-32 [mask-image:linear-gradient(transparent,white,white)] lg:-bottom-32 lg:-top-32 lg:left-[calc(50%+14rem)] lg:right-0 lg:[mask-image:none] dark:[mask-image:linear-gradient(transparent,white,transparent)] lg:dark:[mask-image:linear-gradient(white,white,transparent)]">
              <HeroBackground className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 lg:left-0 lg:translate-x-0 lg:translate-y-[-60%]" />
            </div>
            <div className="relative">
              <Image
                className="absolute -right-64 -top-64"
                src={blurCyanImage}
                alt=""
                width={530}
                height={530}
                unoptimized
                priority
              />
              <Image
                className="absolute -bottom-40 -right-44"
                src={blurIndigoImage}
                alt=""
                width={567}
                height={567}
                unoptimized
                priority
              />
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-primary via-secondary to-logo opacity-10 blur-lg" />
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-primary via-secondary to-logo opacity-10" />
              <div className="relative rounded-2xl bg-[#22222d]/80 ring-1 ring-primary/10 backdrop-blur">
                <div className="absolute -top-px left-20 right-11 h-px bg-gradient-to-r from-primary/10 via-secondary/80 to-primary/10" />
                <div className="absolute -bottom-px left-11 right-20 h-px bg-gradient-to-r from-primary/10 via-secondary/80 to-primary/10" />
                <div className="pl-2 pt-4 md:pl-4">
                  <TrafficLightsIcon className="h-2.5 w-auto stroke-slate-500/30" />
                  <div className="mt-4 flex space-x-2 text-xs">
                    {tabs.map((tab) => (
                      <div
                        key={tab.name}
                        className={clsx(
                          'flex h-6 rounded-full',
                          tab.isActive
                            ? 'bg-gradient-to-r from-primary/10 via-primary to-primary/10 p-px font-medium text-sky-200'
                            : 'text-slate-500',
                        )}
                      >
                        <button
                          className={clsx(
                            'flex items-center rounded-full px-2.5',
                            tab.isActive && 'bg-slate-800',
                          )}
                          onClick={() => toggleTable(tab)}
                        >
                          {tab.name}
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6 flex items-start text-sm md:px-1">
                    <div
                      aria-hidden="true"
                      className="hidden select-none border-r border-slate-300/5 pr-4 font-mono text-slate-600 md:block"
                    >
                      {Array.from({
                        length: currentTab.code.split('\n').length,
                      }).map((_, index) => (
                        <Fragment key={index}>
                          {(index + 1).toString().padStart(2, '0')}
                          <br />
                        </Fragment>
                      ))}
                    </div>
                    <HeroCode code={currentTab.code} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
