declare module "*.png" {
  const value: import("next/dist/shared/lib/get-img-props").StaticImageData
  export default value
}

declare module "*.jpg" {
  const value: import("next/dist/shared/lib/get-img-props").StaticImageData
  export default value
}

declare module "*.jpeg" {
  const value: import("next/dist/shared/lib/get-img-props").StaticImageData
  export default value
}
