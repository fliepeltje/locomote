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
locomote <configs> -i <input-key> -o <output-key>
```

Examples:

Generate assets for input `raw` and output `basic`

```sh
locomote config.in-examples.toml config.out-examples.toml -i raw -o basic
```

Generate multiple outputs for multiple inputs:

```sh
locomote config.in-examples.toml config.out-examples.toml -i raw -i diff -o basic -o yt-code
```

