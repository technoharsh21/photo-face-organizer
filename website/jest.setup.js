import '@testing-library/jest-dom'
import { TextEncoder, TextDecoder } from 'util'

global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

if (typeof global.setImmediate === 'undefined') {
  global.setImmediate = function (fn, ...args) {
    return setTimeout(fn, 0, ...args)
  }
}

if (typeof global.Request === 'undefined') {
  const { Request, Response, Headers } = require('next/dist/compiled/@edge-runtime/primitives')
  global.Request = Request
  global.Response = Response
  global.Headers = Headers
}
