Ansible Collection: gcfg.gcfg
=============================

Ansible collection - `gcfg.gcfg` - to integrate the [GIT-based Configuration Tracking Utility (GCfg)][gcfg].
in Ansible Playbooks.

[gcfg]: https://github.com/cedric-dufour/gcfg


Build and Installation
----------------------

### The Ansible (Galaxy) way

``` shell
git clone https://github.com/cedric-dufour/gcfg.git /path/to/gcfg
cd /path/to/gcfg/ansible
ansible-galaxy collection build
ansible-galaxy collection install gcfg-gcfg-<version>.tar.gz
```

(maybe one day I can be coaxed to publish this to the Ansible Galaxy repository)

### The Debian way

``` shell
git clone https://github.com/cedric-dufour/gcfg.git /path/to/gcfg
cd /path/to/gcfg/ansible
dpkg-buildpackage -us -uc -b
dpkg -i gcfg-ansible_<version>_all.deb
```

Usage
-----

### Initialize the GCfg repository

``` yaml
- name: init
  gcfg.gcfg.init:
```

### Track an existing file

``` yaml
- name: file
  gcfg.gcfg.file:
    state: present
    path: "/etc/sample/foobar"
    flag: ["@SAMPLE"]
    owner: "root"
    group: "root"
    mode: "0644"
```

### Copy and track a file

``` yaml
- name: file
  gcfg.gcfg.copy:
    state: present
    dest: "/etc/sample/foobar"
    src: "foobar"
    flag: ["@SAMPLE"]
    owner: "root"
    group: "root"
    mode: "0644"
```

### Template and track a file

``` yaml
- name: file
  gcfg.gcfg.template:
    state: present
    dest: "/etc/sample/foobar"
    src: "foobar.j2"
    flag: ["@SAMPLE"]
    owner: "root"
    group: "root"
    mode: "0644"
```

### Untrack a file

``` yaml
- name: file
  gcfg.gcfg.file:
    state: absent
    path: "/etc/sample/foobar"
```

### Commit configuration checkpoint

``` yaml
- name: file
  gcfg.gcfg.commit:
    tag: "foobar"
    message: "A sample Git commit message"
```


Development and Tests
---------------------

Verify the `gcfg.gcfg` collection is seen by Ansible:

``` shell
ansible-galaxy collection list
# [output]
#/path/to/gcfg/ansible/ansible_collections
Collection Version
---------- -------
gcfg.gcfg  *
```

If not, you may need to update your environment:

``` shell
export ANSIBLE_COLLECTIONS_PATHS=/path/to/gcfg/ansible:${ANSIBLE_COLLECTIONS_PATHS}
```

As for tests:

``` shell
# Run all tests
cd /path/to/gcfg/ansible/tests
./run

# Run a given test
GCFG_ANSIBLE_TESTS=gcfg_init ./run

# Show debugging information
GCFG_ANSIBLE_DEBUG=yes ./run
```
