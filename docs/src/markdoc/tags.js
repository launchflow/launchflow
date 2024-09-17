import { Callout } from '@/components/Callout'
import { MarkdownImage } from '@/components/MarkdownImage'
import { QuickLink, QuickLinks } from '@/components/QuickLinks'
import { Tag } from '@markdoc/markdoc'
import { TabProvider } from '@/components/TabProvider'
import { Tabs } from '@/components/Tabs'
import { Tab } from '@/components/Tab'
import { FrameImage } from '@/components/FrameImage'
import { GettingStartedSearch } from '@/components/GettingStartedSearch'
import { GettingStartedSelector } from '@/components/GettingStartedSelector'
import { GettingStartedSection } from '@/components/GettingStartedSection'
import { LFInit } from '@/components/LFInit'
import { Cleanup } from '@/components/Cleanup'
import { DeployLaunchflow } from '@/components/DeployLaunchflow'
import { LFCloud } from '@/components/LFCloud'
import { WhatsNext } from '@/components/GettingStartedWhatsNext'

const tags = {
  whatsnext: {
    render: WhatsNext,
  },
  lfcloud: {
    render: LFCloud,
  },
  deploy: {
    render: DeployLaunchflow,
  },
  cleanup: {
    render: Cleanup,
  },
  lfInit: {
    render: LFInit,
  },
  gettingStartedSearch: {
    render: GettingStartedSearch,
  },
  gettingStartedSelector: {
    render: GettingStartedSelector,
    attributes: {
      awsRuntimeOptions: {
        type: Array,
        validate: (value) => value.every((item) => typeof item === 'string'),
      },
      gcpRuntimeOptions: {
        type: Array,
        validate: (value) => value.every((item) => typeof item === 'string'),
      },
    },
  },
  gettingStartedSection: {
    render: GettingStartedSection,
    attributes: {
      cloudProvider: {
        type: String,
      },
      runtime: {
        type: String,
      },
    },
  },
  frameImage: {
    render: FrameImage,
    attributes: {
      src: { type: String },
      alt: { type: String },
      height: { type: Number },
      width: { type: Number },
    },
  },
  tabProvider: {
    render: TabProvider,
    attributes: {
      defaultLabel: { type: String },
    },
    transform(node, config) {
      return new Tag(
        this.render,
        {
          defaultLabel: node.attributes.defaultLabel,
        },
        node.transformChildren(config),
      )
    },
  },
  tabs: {
    render: Tabs,
    attributes: {},
    transform(node, config) {
      const labels = node
        .transformChildren(config)
        .filter((child) => child && child.name === 'Tab')
        .map((tab) => (typeof tab === 'object' ? tab.attributes.label : null))

      return new Tag(this.render, { labels }, node.transformChildren(config))
    },
  },
  tab: {
    render: Tab,
    attributes: {
      label: {
        type: String,
      },
    },
  },
  callout: {
    attributes: {
      type: {
        type: String,
        default: 'note',
        matches: ['note', 'warning'],
        errorLevel: 'critical',
      },
    },
    render: Callout,
  },
  mdimage: {
    attributes: {
      src: { type: String },
      alt: { type: String },
      className: { type: String },
      width: {
        type: Number,
        default: 800,
      },
      height: {
        type: Number,
        default: 800,
      },
    },
    render: MarkdownImage,
  },
  figure: {
    selfClosing: true,
    attributes: {
      src: { type: String },
      alt: { type: String },
      caption: { type: String },
    },
    render: ({ src, alt = '', caption }) => (
      <figure>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} />
        <figcaption>{caption}</figcaption>
      </figure>
    ),
  },
  'quick-links': {
    render: QuickLinks,
  },
  'quick-link': {
    selfClosing: true,
    render: QuickLink,
    attributes: {
      title: { type: String },
      description: { type: String },
      icon: { type: String },
      href: { type: String },
    },
  },
}

export default tags
