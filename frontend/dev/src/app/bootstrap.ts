import Axios, {AxiosStatic} from 'axios'

declare global {
    // Extending the DOM Window Interface
    // noinspection JSUnusedGlobalSymbols
    interface Window {
        axios: AxiosStatic
    }
}

window.axios = Axios
window.axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest'
