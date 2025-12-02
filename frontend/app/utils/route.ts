import { match } from 'path-to-regexp'

export const findMatchingRoute = (path: string) => {    
    const router = useRouter()
    for (const r of router.getRoutes()) {

        const matcher = match(r.path.replace(/:([A-Za-z0-9_]+)\(\)/g, ':$1'), { decode: decodeURIComponent })
        if (matcher(path)) {
            return r
        }
    }
    return null
}
