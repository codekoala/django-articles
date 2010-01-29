$(document).ready(function () {
    $('#id_tags').autocomplete(
        '/blog/ajax/tag/autocomplete/', // if your prefix for articles differs, fix this
        {multiple: true, multipleSeparator: ' '}
    );
});

