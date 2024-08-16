'use client'

import { Fragment } from 'react'
import { Highlight, themes } from 'prism-react-renderer'
import { CopyToClipboard } from 'react-copy-to-clipboard'

export function Fence({
  children,
  language,
}: {
  children: string
  language: string
}) {
  let lineStart = 1
  const linesToHighlight = new Map<number, string>()
  if (language.includes(',')) {
    const split = language.split(',')
    language = split[0]
    lineStart = parseInt(split[1])

    if (split.length > 2) {
      split.slice(2).forEach((x) => {
        let color
        let lineNum
        if (x.endsWith('+') || x.endsWith('-')) {
          lineNum = parseInt(x.slice(0, -1))
          color = x.slice(-1) === '+' ? 'bg-green-800' : 'bg-red-800'
        } else {
          lineNum = parseInt(x)
          color = 'bg-indigo-800'
        }
        linesToHighlight.set(lineNum, color)
      })
    }
  }
  const code = children.trimEnd()
  return (
    <div className="relative">
      <Highlight code={code} language={language} theme={themes.nightOwl}>
        {({ className, style, tokens, getTokenProps }) => (
          <pre className={className} style={{ ...style, padding: 0 }}>
            <code className="inline-grid sm:inline">
              {tokens.map((line, lineIndex) => {
                const lineNumber = lineStart + lineIndex
                const highlightClass = linesToHighlight.get(lineNumber) || ''
                let paddingTop = '0'
                let paddingBottom = '0'
                // These values came from materialize, I think they're hardcoded but didn't check
                if (lineIndex === 0) {
                  paddingTop = '0.8571429em'
                }
                if (lineIndex === tokens.length - 1) {
                  paddingBottom = '0.8571429em'
                }

                // Not sure why min width is needed on the span but without it the line numbers aren't uniform size always on mobile
                return (
                  <Fragment key={lineIndex}>
                    <div className="flex w-full">
                      <span
                        style={{
                          minWidth: '2.5rem',
                          paddingTop: paddingTop,
                          paddingBottom: paddingBottom,
                        }}
                        className={`inline-block w-10 select-none bg-opacity-70 pr-3 text-right text-gray-500 ${highlightClass}`}
                      >
                        {lineNumber}
                      </span>
                      <div
                        style={{
                          paddingTop: paddingTop,
                          paddingBottom: paddingBottom,
                        }}
                        className={`w-full bg-opacity-50 ${highlightClass}`}
                      >
                        {line
                          .filter((token) => !token.empty)
                          .map((token, tokenIndex) => (
                            <span
                              key={tokenIndex}
                              {...getTokenProps({ token })}
                            />
                          ))}
                        {'\n'}
                      </div>
                    </div>
                  </Fragment>
                )
              })}
            </code>
            <CopyToClipboard text={code}>
              <button className="material-symbols-outlined absolute right-2 top-2 text-[#d6deeb] hover:text-primary">
                content_copy
              </button>
            </CopyToClipboard>
          </pre>
        )}
      </Highlight>
    </div>
  )
}
