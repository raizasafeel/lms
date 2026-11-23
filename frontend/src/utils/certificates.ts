import { toast } from 'frappe-ui'
import { useClipboard } from '@vueuse/core'
import dayjs from '@/utils/dayjs'
import { openExternal } from '@/utils/openExternal'

export type CertificateStatus = 'valid' | 'expired' | 'unpublished'

export interface CertificateMember {
	full_name: string
	username: string | null
	user_image: string | null
	headline: string | null
}

export interface CertificateAwardedFor {
	name: string
	title: string
	category: string | null
	description: string | null
	image: string | null
}

export interface CertificateDetails {
	name: string
	kind: 'course' | 'batch'
	title: string
	status: CertificateStatus
	issue_date: string
	expiry_date: string | null
	evaluator_name: string | null
	issued_by: string
	is_member: boolean
	member: CertificateMember
	awarded_for: CertificateAwardedFor | null
	html: string | null
}

export const formatCertificateDate = (date: string): string =>
	dayjs(date).format('DD MMM YYYY')

/** The short URL printed as a QR code on the certificate; the server redirects it here. */
export const certificateLink = (name: string): string =>
	`${window.location.origin}/certificates/${encodeURIComponent(name)}`

export const certificatePdfUrl = (name: string): string =>
	`/api/method/lms.lms.api.download_certificate_pdf?certificate=${encodeURIComponent(
		name
	)}`

export const downloadCertificate = (name: string): void =>
	openExternal(certificatePdfUrl(name))

export const linkedInShareUrl = (name: string): string =>
	`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(
		certificateLink(name)
	)}`

export const emailShareUrl = (name: string, title: string): string =>
	`mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(
		certificateLink(name)
	)}`

/** Copies a certificate's link; `legacy` covers sites served over plain http. */
export function useCopyCertificateLink() {
	const { copy } = useClipboard({ legacy: true })
	return async (name: string): Promise<void> => {
		try {
			await copy(certificateLink(name))
			toast.success(__('Link copied'))
		} catch {
			toast.error(__('Could not copy the link'))
		}
	}
}
