GIT-based Configuration Tracking Utility (GCFG)
===============================================


BUILD
-----

NOTE: By "build", we mean create the necessary tarballs/package required for
      installation (according to the INSTALL section below) or distribution.

1. [MUST] Obtain the source code:

``` shell
git clone https://github.com/cedric-dufour/gcfg
```

   OR

``` shell
tar -xjf gcfg-source-@version@.tar.bz2
cd gcfg-source-@version@
```

2. [MAY] (Re-)build the source tarball:

``` shell
./debian/rules build-source-tarball
ls -al ../gcfg-source-@version@.tar.bz2
```

3. [MAY] Build the installation (release) tarball:

``` shell
./debian/rules build-install-tarball
ls -al ../gcfg-@version@.tar.bz2
```

4. [MAY] Build the debian packages:

``` shell
dpkg-buildpackage -us -uc -b
ls -al ../gcfg_@version@_all.deb ../gcfg-doc_@version@_all.deb
```

5. [MAY] Build the debian source package:

``` shell
debuild -I'.git*' -I'*.pyc' -us -uc -S
ls -al ../gcfg_@version@.dsc ../gcfg_@version@.tar.gz
```

OR

2-5. [SHOULD] Do it all with a single command

``` shell
./debian/rules release
```


INSTALL
-------

1. [MUST] Installation:

   a. using the release tarball:

``` shell
INSTALL_DIR='<installation-directory>'
cd "${INSTALL_DIR}"
tar -xjf gcfg-@version@.tar.bz2
```

      OR

   b. using the debian package:

``` shell
dpkg -i gcfg_@version@_all.deb
```
