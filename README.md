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

