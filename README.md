Ever wanted to give **motion** to your **l**ines **o**f **c**ode? - Now you can using **locomote**!

## Installation

The recommended method is to use `pipx`:

```sh
pipx install "git+https://github.com/fliepeltje/locomote"
```

## Usage

First, create a config file.
Refer to the [example](config.example.toml) and the [source](locomote/config.py) for references (until docs materialize).

Every key in the `toml` file corresponds to a single `locomote` config; 1 file can house multiple configs.

To run:

```sh
locomote <cnofig-path> <config-key>
```

## Demos


### Simple File

Go from blank file to your target file:

```sh
locomote config.example.toml my-file
```

![[File Clip](examples/my-file/tail.png)](examples/my-file/clip.mp4)

### File Diff

Create a clip for every commit associated to a file

```sh
locomote config.example.toml my-file-diff
```

![[Diff Clip 1](examples/my-file-diff/000-add-makedirs-head.png)](examples/my-file-diff/000-add-makedirs-clip.mp4)
![[Diff Clip 2](examples/my-file-diff/001-add-os-iter-head.png)](examples/my-file-diff/001-add-os-iter-clip.mp4)
![[Diff Clip 3](examples/my-file-diff/002-add-pathlib-head.png)](examples/my-file-diff/002-add-pathlib-clip.mp4)


### Command + Log output

Create an animated output of your command

```sh
locomote config.example.toml fly-apps-list
```

![[File Clip](examples/fly-apps-list/tail.png)](examples/fly-apps-list/clip.mp4)