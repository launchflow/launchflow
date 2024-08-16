
import { theme } from '@/lib/heroPrismTheme'
import clsx from 'clsx'
import { Highlight } from 'prism-react-renderer'


type HeroCodeProps = {
    code: string;

}
export function HeroCode({ code }: HeroCodeProps) {
    return (<Highlight
        code={code}
        language="python"
        theme={theme}
    >
        {({
            className,
            style,
            tokens,
            getLineProps,
            getTokenProps,
        }) => (
            <pre
                className={clsx(
                    className,
                    'flex overflow-x-auto pb-6',
                )}
                style={style}
            >
                <code className="px-4">
                    {tokens.map((line, lineIndex) => (
                        <div key={lineIndex} {...getLineProps({ line })}>
                            {line.map((token, tokenIndex) => (
                                <span
                                    key={tokenIndex}
                                    {...getTokenProps({ token })}
                                />
                            ))}
                        </div>
                    ))}
                </code>
            </pre>
        )}
    </Highlight>)
}
