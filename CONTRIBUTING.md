# Contributing

Thank you for helping. Anyone can raise a question, report a problem or propose a change. You do not need to write code.

## Ways to take part

- **Ask or report:** the [contact form](https://github.com/cyberdudeuk/dcat-uk-ap/issues/new?template=contact.yml).
- **Propose a change to the profile:** the [change request form](https://github.com/cyberdudeuk/dcat-uk-ap/issues/new?template=change-request.yml). Say what users need, your evidence, and what it means for records that already exist.
- **Report a defect in the portal or the files:** the [defect form](https://github.com/cyberdudeuk/dcat-uk-ap/issues/new?template=defect.yml).

All forms are public. Do not include personal data, colleagues' names, or anything above OFFICIAL.

## How changes are decided

1. **Ask.** A change request is raised.
2. **Assess.** Maintainers check it against DCAT 3, DCAT-AP and the backlog, and say whether it is a major, minor or patch change.
3. **Discuss.** Major and minor changes go to the Metadata Implementation Working Group.
4. **Decide.** The owning team decides; major changes go to the Data Standards Authority for endorsement.
5. **Release.** The change ships in the next release, after the release gate passes.

Versioning: a **major** release makes something mandatory that was not, removes a property or closes a codelist value; a **minor**
release adds a property, a value or a recommendation; a **patch** fixes wording, examples or guidance.

## Making a change in code

- Edit the source only: `profile/`, `content/`, `examples/`, `site_src/` or `tools/`. Never edit `site/` or `docs/registers.md`; they are generated.
- Work on a short-lived branch and open a pull request. Commit summaries of 50 characters or fewer (the GDS Way).
- Run the checks in the README before you push. CI runs them all again.
- **Every defect gets a check in the same commit as its fix**, with a deliberate break proving the check fails, and an entry in
  `content/portal.yaml` (`governance.defects`). The check suite never shrinks.
- No email address anywhere: page, metadata, data, comments or examples. Test fixtures may use reserved example domains only.
- No decks or films in the repository.
- Pages load nothing from another host: no CDN, web font or analytics.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
