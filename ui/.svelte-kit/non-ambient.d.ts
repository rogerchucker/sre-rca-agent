
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/action" | "/incident" | "/incident/[id]" | "/knowledge" | "/signals" | "/systems";
		RouteParams(): {
			"/incident/[id]": { id: string }
		};
		LayoutParams(): {
			"/": { id?: string };
			"/action": Record<string, never>;
			"/incident": { id?: string };
			"/incident/[id]": { id: string };
			"/knowledge": Record<string, never>;
			"/signals": Record<string, never>;
			"/systems": Record<string, never>
		};
		Pathname(): "/" | "/action" | "/action/" | "/incident" | "/incident/" | `/incident/${string}` & {} | `/incident/${string}/` & {} | "/knowledge" | "/knowledge/" | "/signals" | "/signals/" | "/systems" | "/systems/";
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): string & {};
	}
}