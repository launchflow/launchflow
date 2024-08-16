import withMarkdoc from '@markdoc/next.js'
import withSearch from './src/markdoc/search.mjs'

/** @type {import('next').NextConfig} */
const nextConfig = {
  pageExtensions: ['js', 'jsx', 'md', 'ts', 'tsx'],
  redirects: async () => {
    return [
      {
        source: '/buildflow/introduction',
        destination: '/',
        permanent: true,
      },
    ]
  },
}

export default withSearch(
  withMarkdoc({ schemaPath: './src/markdoc' })(nextConfig),
)
