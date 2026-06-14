import { build } from 'vite'
import { createInlineViteConfig } from './vite-config.mjs'

await build(createInlineViteConfig())
