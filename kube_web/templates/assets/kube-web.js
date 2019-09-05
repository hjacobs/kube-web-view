// https://bulma.io/documentation/components/navbar/
document.addEventListener('DOMContentLoaded', () => {

  // Get all "navbar-burger" elements
  const $toggleButtons = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger, .aside-burger, .toggle-tools'), 0);

  // Check if there are any navbar burgers
  if ($toggleButtons.length > 0) {

    // Add a click event on each of them
    $toggleButtons.forEach( el => {
      el.addEventListener('click', () => {

        // Get the target from the "data-target" attribute
        const target = el.dataset.target;
        const $target = document.getElementById(target);

        // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
        el.classList.toggle('is-active');
        $target.classList.toggle('is-active');

      });
    });
  }

  const $unselectButtons = Array.prototype.slice.call(document.querySelectorAll('.unselect'), 0);

  if ($unselectButtons.length > 0) {

    $unselectButtons.forEach( el => {
      el.addEventListener('click', () => {

        // Get the target from the "data-target" attribute
        const target = el.dataset.target;

        const $inputs = Array.prototype.slice.call(document.querySelectorAll('#' + target + ' input[type=checkbox]'), 0);
        $inputs.forEach( inp => {
            inp.checked = false;
        });

      });
    });
  }

  const $forms = Array.prototype.slice.call(document.querySelectorAll('form.tools-form'), 0);

  $forms.forEach( el => {
    el.addEventListener('submit', function () {
      const $inputs = Array.prototype.slice.call(el.getElementsByTagName('input'), 0);
      $inputs.forEach( input => {
        // setting the "name" attribute to empty will prevent having an empty query parameter in the URL
        if (input.name && !input.value) {
            input.name = '';
        }
      });
    });
  });

  const $collapsibleHeaders = Array.prototype.slice.call(document.querySelectorAll('main .collapsible h4.title'), 0);

  $collapsibleHeaders.forEach( el => {
    el.addEventListener('click', function () {
      const $section = el.parentElement;
      $section.classList.toggle('is-collapsed');
    });
  });

});
