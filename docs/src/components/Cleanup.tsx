import { Fence } from './Fence'

const destroy = `lf destroy
lf environments delete
`

export function Cleanup() {
  return (
    <div>
      <p>
        Optionally you can delete all your resources, service, and environments
        with:
      </p>
      <Fence language="bash">{destroy}</Fence>
    </div>
  )
}
