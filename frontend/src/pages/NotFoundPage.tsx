import { Link } from 'react-router-dom';
import { useT } from '../i18n';
import { PageHeader } from '../components/ui/PageHeader';

export function NotFoundPage() {
  const t = useT();
  return (
    <section>
      <PageHeader title={t('page.notFound.title')} />
      <Link to="/" className="text-teal underline underline-offset-4">
        {t('page.notFound.back')}
      </Link>
    </section>
  );
}
